/*
  AIMathStudentAuth (frontend)
  -  Student login (name + parent PIN)
  -  Generates shareable report URLs for parents
  -  Persists to localStorage

  Storage:
    key = aimath_student_auth_v1
    value = { version:1, name, pin, created_at }
*/
(function(){
  'use strict';

  const LS_KEY = 'aimath_student_auth_v1';
  const VERSION = 1;

  /* ─── helpers ─── */
  function safeJson(s, fb){ try { return JSON.parse(s); } catch { return fb; } }
  function nowIso(){ return new Date().toISOString(); }

  /* ─── load / save ─── */
  function load(){
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return null;
      const o = safeJson(raw, null);
      if (o && o.version === VERSION && o.name && o.pin) return o;
    } catch {}
    return null;
  }

  function save(o){
    try { localStorage.setItem(LS_KEY, JSON.stringify(o)); } catch {}
  }

  /* ─── public API ─── */
  function isLoggedIn(){
    return !!load();
  }

  function getCurrentStudent(){
    return load();
  }

  function login(name, pin){
    if (!name || !String(name).trim()) throw new Error('請輸入學生暱稱');
    const p = String(pin || '').trim();
    if (!/^\d{4,6}$/.test(p)) throw new Error('家長密碼需 4~6 位數字');
    const o = {
      version: VERSION,
      name: String(name).trim(),
      pin: p,
      created_at: nowIso()
    };
    save(o);
    return o;
  }

  function logout(){
    try { localStorage.removeItem(LS_KEY); } catch {}
  }

  function verifyPin(input){
    const s = load();
    if (!s) return false;
    return String(input || '').trim() === s.pin;
  }

  /* ─── report data collector ─── */
  function collectReportData(days){
    const d = Number(days) || 7;
    const cutoff = Date.now() - d * 86400000;
    const student = load();
    const name = student ? student.name : '未登入';

    /* collect from exam-sprint localStorage */
    let sprintAttempts = [];
    try {
      const raw = localStorage.getItem('examSprint.v1');
      if (raw) {
        const obj = safeJson(raw, null);
        if (obj && Array.isArray(obj.attempts)){
          sprintAttempts = obj.attempts.filter(a => Number(a.ts || a.timestamp || 0) >= cutoff);
        }
      }
    } catch {}

    /* collect from AIMathAttemptTelemetry */
    let telAttempts = [];
    try {
      const uid = window.AIMathCoachLog?.getOrCreateUserId?.() || 'guest';
      const items = window.AIMathAttemptTelemetry?.listAttempts?.(uid, { sinceMs: cutoff }) || [];
      telAttempts = items;
    } catch {}

    /* merge (deduplicate by ts) */
    const seen = new Set();
    const all = [];
    for (const a of [...sprintAttempts, ...telAttempts]){
      const ts = Number(a.ts || a.ts_end || a.timestamp || 0);
      const key = `${ts}_${a.question_id || a.qid || ''}`;
      if (seen.has(key)) continue;
      seen.add(key);
      all.push(a);
    }

    /* ── normalizer: handle both flat (exam-sprint) and nested (telemetry) fields ── */
    function getTimeMs(a){
      if (a.time_ms) return Number(a.time_ms);
      if (a.time_spent_ms) return Number(a.time_spent_ms);
      const s = Number(a.ts_start || 0), e = Number(a.ts_end || 0);
      if (s > 0 && e > 0 && e > s) return e - s;
      return 0;
    }
    function getMaxHint(a){
      if (a.max_hint != null) return Number(a.max_hint);
      if (a.hint && Array.isArray(a.hint.shown_levels) && a.hint.shown_levels.length)
        return Math.max.apply(null, a.hint.shown_levels);
      if (a.hint && a.hint.shown_count) return Math.min(3, Number(a.hint.shown_count));
      return 0;
    }
    function getTopic(a){
      return a.unit_id || a.topic || a.topic_id || '未分類';
    }
    function getKind(a){
      return a.kind || a.template_id || '';
    }
    function getQuestionText(a){
      if (a.question_text) return a.question_text;
      if (a.question) return a.question;
      if (a.extra && a.extra.question) return a.extra.question;
      return '';
    }

    /* summarize */
    const total = all.length;
    const correct = all.filter(a => a.ok || a.is_correct).length;
    const accuracy = total ? Math.round(correct / total * 100) : 0;
    const totalMs = all.reduce((s, a) => s + (getTimeMs(a) || 0), 0);
    const avgMs = total ? Math.round(totalMs / total) : 0;

    /* hint distribution */
    const hintDist = [0, 0, 0, 0]; // 0,1,2,3
    for (const a of all){
      const h = Math.max(0, Math.min(3, getMaxHint(a)));
      hintDist[h]++;
    }

    /* weakness */
    const byKey = {};
    for (const a of all){
      const topic = getTopic(a);
      const kind = getKind(a);
      const key = `${topic}__${kind}`;
      if (!byKey[key]) byKey[key] = { topic, kind, n: 0, wrong: 0, h2: 0, h3: 0 };
      byKey[key].n++;
      if (!(a.ok || a.is_correct)) byKey[key].wrong++;
      if (getMaxHint(a) >= 2) byKey[key].h2++;
      if (getMaxHint(a) >= 3) byKey[key].h3++;
    }
    const weak = Object.values(byKey)
      .map(x => { x.score = x.wrong * 1.0 + x.h2 * 0.25 + x.h3 * 0.25; return x; })
      .filter(x => x.wrong >= 1)
      .sort((a, b) => b.score - a.score || b.wrong - a.wrong)
      .slice(0, 5)
      .map(w => ({ t: w.topic, k: w.kind, w: w.wrong, n: w.n, h2: w.h2, h3: w.h3 }));

    /* recent wrong (last 5) */
    const wrongList = all
      .filter(a => !(a.ok || a.is_correct))
      .slice(-5)
      .map(a => ({
        q: String(getQuestionText(a)).substring(0, 60),
        sa: String(a.student_answer_raw || a.student_answer || '').substring(0, 20),
        ca: String(a.correct_answer || a.answer || '').substring(0, 20),
        t: getTopic(a),
        k: getKind(a),
        et: a.error_type || '',
        ed: String(a.error_detail || '').substring(0, 60)
      }));

    /* daily breakdown (last N days) */
    const daily = {};
    for (const a of all){
      const ts = Number(a.ts || a.ts_end || a.timestamp || 0);
      const day = new Date(ts).toISOString().slice(0, 10);
      if (!daily[day]) daily[day] = { n: 0, ok: 0 };
      daily[day].n++;
      if (a.ok || a.is_correct) daily[day].ok++;
    }

    /* module breakdown */
    const byMod = {};
    for (const a of all){
      const mod = a.unit_id || a.module || a.moduleId || a.topic || a.topic_id || '未分類';
      if (!byMod[mod]) byMod[mod] = { n: 0, ok: 0 };
      byMod[mod].n++;
      if (a.ok || a.is_correct) byMod[mod].ok++;
    }
    const modules = Object.entries(byMod)
      .map(([m, v]) => ({ m, n: v.n, ok: v.ok, acc: v.n ? Math.round(v.ok / v.n * 100) : 0 }))
      .sort((a, b) => b.n - a.n);

    /* last 24h snapshot */
    var cutoff24 = Date.now() - 86400000;
    var last24 = all.filter(function(a){
      var ts = Number(a.ts || a.ts_end || a.timestamp || 0);
      return ts >= cutoff24;
    });
    var h24total = last24.length;
    var h24correct = last24.filter(function(a){ return a.ok || a.is_correct; }).length;
    var h24accuracy = h24total ? Math.round(h24correct / h24total * 100) : 0;
    var h24totalMs = last24.reduce(function(s, a){ return s + (getTimeMs(a) || 0); }, 0);
    var h24avgMs = h24total ? Math.round(h24totalMs / h24total) : 0;
    var h24hint = [0,0,0,0];
    for (var hi = 0; hi < last24.length; hi++){
      var hv = Math.max(0, Math.min(3, getMaxHint(last24[hi])));
      h24hint[hv]++;
    }
    var h24byMod = {};
    for (var mi = 0; mi < last24.length; mi++){
      var ma = last24[mi];
      var mm = ma.unit_id || ma.module || ma.moduleId || ma.topic || ma.topic_id || '未分類';
      if (!h24byMod[mm]) h24byMod[mm] = { n:0, ok:0 };
      h24byMod[mm].n++;
      if (ma.ok || ma.is_correct) h24byMod[mm].ok++;
    }
    var h24modules = Object.keys(h24byMod).map(function(k){
      var v = h24byMod[k];
      return { m:k, n:v.n, ok:v.ok, acc: v.n ? Math.round(v.ok/v.n*100) : 0 };
    }).sort(function(a,b){ return b.n - a.n; });

    return {
      v: 1,
      name,
      ts: Date.now(),
      days: d,
      d: {
        total, correct, accuracy, avgMs,
        hintDist,
        weak,
        wrong: wrongList,
        daily,
        modules,
        h24: {
          total: h24total, correct: h24correct, accuracy: h24accuracy,
          avgMs: h24avgMs, hintDist: h24hint, modules: h24modules
        }
      }
    };
  }

  /* ─── URL encoder / decoder ─── */
  function encodeReportUrl(data, pin){
    const payload = { ...data, pin: String(pin || '') };
    const json = JSON.stringify(payload);
    const encoded = btoa(unescape(encodeURIComponent(json)));
    /* find parent-report page relative to current page */
    const base = window.location.pathname.replace(/[^/]*$/, '');
    const reportPath = base.includes('/docs/')
      ? base.replace(/\/docs\/.*$/, '/docs/parent-report/')
      : '../parent-report/';
    return window.location.origin + reportPath + '?d=' + encodeURIComponent(encoded);
  }

  function decodeReportUrl(encodedStr){
    try {
      const json = decodeURIComponent(escape(atob(decodeURIComponent(encodedStr))));
      return JSON.parse(json);
    } catch { return null; }
  }

  /* ─── Cloud Sync (jsonblob.com) ─── */
  var CLOUD_API = 'https://jsonblob.com/api/jsonBlob';
  var REGISTRY_BLOB_ID = '019ca94d-1492-7aeb-a2bb-c17c391d6f22';
  var _cloudTimer = null;

  function scheduleCloudSync(){
    if (!isLoggedIn()) return;
    if (_cloudTimer) clearTimeout(_cloudTimer);
    _cloudTimer = setTimeout(doCloudSync, 3000);
  }

  /**
   * Sync report data directly into the shared registry blob.
   * Registry structure: { entries: { "KAI": { pin, data, cloud_ts } } }
   * One blob for all students — no per-student blob needed.
   */
  function doCloudSync(){
    if (!isLoggedIn()) return;
    try {
      var reportData = collectReportData(7);
      var student = load();
      if (!student) return;
      var nameKey = student.name.trim();
      var entry = {
        pin: student.pin || '',
        data: reportData,
        cloud_ts: Date.now()
      };

      fetch(CLOUD_API + '/' + REGISTRY_BLOB_ID, {
        headers: { 'Accept': 'application/json' }
      })
      .then(function(resp){ return resp.json(); })
      .then(function(reg){
        if (!reg || typeof reg !== 'object') reg = {};
        if (!reg.entries) reg.entries = {};
        reg.entries[nameKey] = entry;
        return fetch(CLOUD_API + '/' + REGISTRY_BLOB_ID, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(reg)
        });
      })
      .catch(function(){});
    } catch(e){}
  }

  /**
   * Look up a student's report from the shared registry blob.
   * Returns { pin, data, cloud_ts } or null.
   */
  function lookupStudentReport(name){
    var nameKey = String(name || '').trim();
    if (!nameKey) return Promise.resolve(null);
    return fetch(CLOUD_API + '/' + REGISTRY_BLOB_ID, {
      headers: { 'Accept': 'application/json' }
    })
    .then(function(resp){
      if (!resp.ok) return null;
      return resp.json();
    })
    .then(function(reg){
      if (!reg || !reg.entries) return null;
      return reg.entries[nameKey] || null;
    })
    .catch(function(){ return null; });
  }

  /* hook into AIMathAttemptTelemetry.appendAttempt to auto-sync */
  function hookTelemetryForCloudSync(){
    if (!window.AIMathAttemptTelemetry) return;
    if (!window.AIMathAttemptTelemetry.appendAttempt) return;
    if (window.AIMathAttemptTelemetry._cloudHooked) return;
    var orig = window.AIMathAttemptTelemetry.appendAttempt;
    window.AIMathAttemptTelemetry.appendAttempt = function(){
      var result = orig.apply(this, arguments);
      scheduleCloudSync();
      return result;
    };
    window.AIMathAttemptTelemetry._cloudHooked = true;
  }

  /* ─── login UI (inject floating button + modal) ─── */
  function injectLoginUI(containerEl){
    if (!containerEl) return;

    const student = load();

    const wrapper = document.createElement('div');
    wrapper.id = 'studentAuthUI';
    wrapper.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;';

    /* compute parent-report path relative to current page */
    var parentReportHref = '../parent-report/';
    try {
      var base = window.location.pathname.replace(/[^/]*$/, '');
      if (base.indexOf('/docs/') !== -1){
        parentReportHref = base.replace(/\/docs\/.*$/, '/docs/parent-report/');
      }
    } catch(e){}

    var reportLink = parentReportHref;

    if (student){
      wrapper.innerHTML = `
        <span style="font-size:13px;color:var(--muted,#9aa4b2)">👤 <strong style="color:var(--text,#e6edf3)">${escHtml(student.name)}</strong></span>
        <a href="${reportLink}" id="btnParentReport" style="text-decoration:none"><button class="btn ghost" style="font-size:12px;padding:6px 10px" type="button">📊 家長報告</button></a>
        <button class="btn ghost" id="btnLogout" style="font-size:12px;padding:6px 10px">登出</button>
      `;
    } else {
      wrapper.innerHTML = `
        <button class="btn" id="btnLoginShow" style="font-size:12px;padding:6px 10px">🔑 學生登入</button>
        <span style="font-size:11px;color:var(--muted,#9aa4b2)">登入後可查看家長報告</span>
      `;
    }

    containerEl.appendChild(wrapper);

    /* modal HTML */
    const modal = document.createElement('div');
    modal.id = 'authModal';
    modal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:9999;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--card,#121c3d);border:1px solid var(--line,#243055);border-radius:16px;padding:24px;max-width:380px;width:90%;color:var(--text,#e6edf3);">
        <h3 style="margin:0 0 16px 0">🔑 學生登入</h3>
        <div style="margin-bottom:12px">
          <label style="font-size:13px;color:var(--muted,#9aa4b2)">學生暱稱</label>
          <input id="authName" style="width:100%;margin-top:4px;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(0,0,0,.22);color:var(--text,#e6edf3);font-size:15px" placeholder="例：小明" />
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:13px;color:var(--muted,#9aa4b2)">家長密碼（4~6位數字，給家長看報告用）</label>
          <input id="authPin" type="password" style="width:100%;margin-top:4px;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(0,0,0,.22);color:var(--text,#e6edf3);font-size:15px" placeholder="例：1234" maxlength="6" />
        </div>
        <div id="authError" style="color:#f85149;font-size:13px;margin-bottom:8px;display:none"></div>
        <div style="display:flex;gap:10px">
          <button id="authSubmit" style="flex:1;padding:10px;border-radius:10px;border:none;background:#2ea043;color:#fff;font-weight:800;font-size:15px;cursor:pointer">登入</button>
          <button id="authCancel" style="padding:10px 16px;border-radius:10px;border:1px solid rgba(255,255,255,.18);background:transparent;color:var(--text,#e6edf3);cursor:pointer">取消</button>
        </div>
        <div style="margin-top:12px;font-size:11px;color:var(--muted,#9aa4b2);line-height:1.6">
          💡 登入後，家長可在任何裝置打開「📊 家長報告」，<br>輸入相同暱稱 + 密碼即可查看。每做一題都會自動更新。
        </div>
      </div>
    `;
    document.body.appendChild(modal);



    /* event handlers */
    const btnLogin = document.getElementById('btnLoginShow');
    const btnLogout = document.getElementById('btnLogout');

    if (btnLogin){
      btnLogin.addEventListener('click', () => {
        modal.style.display = 'flex';
        document.getElementById('authName')?.focus();
      });
    }

    if (btnLogout){
      btnLogout.addEventListener('click', () => {
        if (confirm('確定登出？（作答紀錄仍保留在本機）')) {
          logout();
          location.reload();
        }
      });
    }

    document.getElementById('authSubmit')?.addEventListener('click', () => {
      const errEl = document.getElementById('authError');
      try {
        const name = document.getElementById('authName')?.value;
        const pin = document.getElementById('authPin')?.value;
        login(name, pin);
        modal.style.display = 'none';
        location.reload();
      } catch (e) {
        if (errEl){ errEl.textContent = e.message; errEl.style.display = 'block'; }
      }
    });

    document.getElementById('authCancel')?.addEventListener('click', () => {
      modal.style.display = 'none';
    });

    /* Enter key in modal */
    document.getElementById('authPin')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('authSubmit')?.click();
    });
    document.getElementById('authName')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('authPin')?.focus();
    });

    /* Click outside to close */
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

    /* ─── Auto cloud sync on page load + hook telemetry ─── */
    if (isLoggedIn()){
      scheduleCloudSync();
      hookTelemetryForCloudSync();
    }
  }

  function escHtml(s){
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  /* ─── export ─── */
  window.AIMathStudentAuth = {
    VERSION,
    isLoggedIn,
    getCurrentStudent,
    login,
    logout,
    verifyPin,
    collectReportData,
    encodeReportUrl,
    decodeReportUrl,
    injectLoginUI,
    scheduleCloudSync,
    lookupStudentReport
  };
})();
