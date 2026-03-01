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

    /* summarize */
    const total = all.length;
    const correct = all.filter(a => a.ok || a.is_correct).length;
    const accuracy = total ? Math.round(correct / total * 100) : 0;
    const totalMs = all.reduce((s, a) => s + (Number(a.time_ms || a.time_spent_ms || 0) || 0), 0);
    const avgMs = total ? Math.round(totalMs / total) : 0;

    /* hint distribution */
    const hintDist = [0, 0, 0, 0]; // 0,1,2,3
    for (const a of all){
      const h = Math.max(0, Math.min(3, Number(a.max_hint || 0)));
      hintDist[h]++;
    }

    /* weakness */
    const byKey = {};
    for (const a of all){
      const topic = a.topic || a.topic_id || '未分類';
      const kind = a.kind || a.template_id || '';
      const key = `${topic}__${kind}`;
      if (!byKey[key]) byKey[key] = { topic, kind, n: 0, wrong: 0, h2: 0, h3: 0 };
      byKey[key].n++;
      if (!(a.ok || a.is_correct)) byKey[key].wrong++;
      if ((Number(a.max_hint || 0)) >= 2) byKey[key].h2++;
      if ((Number(a.max_hint || 0)) >= 3) byKey[key].h3++;
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
        q: String(a.question_text || a.question || '').substring(0, 60),
        sa: String(a.student_answer_raw || a.student_answer || '').substring(0, 20),
        ca: String(a.correct_answer || a.answer || '').substring(0, 20),
        t: a.topic || a.topic_id || '',
        k: a.kind || a.template_id || '',
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
      const mod = a.module || a.moduleId || a.topic || a.topic_id || '未分類';
      if (!byMod[mod]) byMod[mod] = { n: 0, ok: 0 };
      byMod[mod].n++;
      if (a.ok || a.is_correct) byMod[mod].ok++;
    }
    const modules = Object.entries(byMod)
      .map(([m, v]) => ({ m, n: v.n, ok: v.ok, acc: v.n ? Math.round(v.ok / v.n * 100) : 0 }))
      .sort((a, b) => b.n - a.n);

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
        modules
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

  /* ─── login UI (inject floating button + modal) ─── */
  function injectLoginUI(containerEl){
    if (!containerEl) return;

    const student = load();

    const wrapper = document.createElement('div');
    wrapper.id = 'studentAuthUI';
    wrapper.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;';

    if (student){
      wrapper.innerHTML = `
        <span style="font-size:13px;color:var(--muted,#9aa4b2)">👤 <strong style="color:var(--text,#e6edf3)">${escHtml(student.name)}</strong></span>
        <button class="btn ghost" id="btnGenReport" style="font-size:12px;padding:6px 10px">📊 生成家長報告連結</button>
        <button class="btn ghost" id="btnLogout" style="font-size:12px;padding:6px 10px">登出</button>
      `;
    } else {
      wrapper.innerHTML = `
        <button class="btn" id="btnLoginShow" style="font-size:12px;padding:6px 10px">🔑 學生登入</button>
        <span style="font-size:11px;color:var(--muted,#9aa4b2)">登入後家長可遠端查看作答報告</span>
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
          💡 登入後，點「生成家長報告連結」可產生一個網址，<br>家長在手機/電腦上打開即可遠端查看孩子作答狀況。
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    /* report URL modal */
    const reportModal = document.createElement('div');
    reportModal.id = 'reportModal';
    reportModal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:9999;align-items:center;justify-content:center;';
    reportModal.innerHTML = `
      <div style="background:var(--card,#121c3d);border:1px solid var(--line,#243055);border-radius:16px;padding:24px;max-width:480px;width:90%;color:var(--text,#e6edf3);">
        <h3 style="margin:0 0 12px 0">📊 家長報告連結</h3>
        <div style="font-size:13px;color:var(--muted,#9aa4b2);margin-bottom:12px">
          把下面連結傳給家長（LINE / WhatsApp），打開後輸入家長密碼即可查看。
        </div>
        <textarea id="reportUrlText" readonly style="width:100%;min-height:80px;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(0,0,0,.22);color:var(--accent,#58a6ff);font-size:12px;word-break:break-all;resize:vertical"></textarea>
        <div style="display:flex;gap:10px;margin-top:12px">
          <button id="reportCopy" style="flex:1;padding:10px;border-radius:10px;border:none;background:#1f6feb;color:#fff;font-weight:800;cursor:pointer">📋 複製連結</button>
          <button id="reportClose" style="padding:10px 16px;border-radius:10px;border:1px solid rgba(255,255,255,.18);background:transparent;color:var(--text,#e6edf3);cursor:pointer">關閉</button>
        </div>
        <div id="reportCopyMsg" style="color:#2ea043;font-size:13px;margin-top:8px;display:none">✅ 已複製！</div>
      </div>
    `;
    document.body.appendChild(reportModal);

    /* event handlers */
    const btnLogin = document.getElementById('btnLoginShow');
    const btnLogout = document.getElementById('btnLogout');
    const btnGenReport = document.getElementById('btnGenReport');

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

    if (btnGenReport){
      btnGenReport.addEventListener('click', () => {
        const s = load();
        if (!s){ alert('請先登入'); return; }
        const data = collectReportData(7);
        const url = encodeReportUrl(data, s.pin);
        document.getElementById('reportUrlText').value = url;
        reportModal.style.display = 'flex';
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

    document.getElementById('reportCopy')?.addEventListener('click', async () => {
      const txt = document.getElementById('reportUrlText')?.value;
      if (!txt) return;
      try {
        await navigator.clipboard.writeText(txt);
        const msg = document.getElementById('reportCopyMsg');
        if (msg){ msg.style.display = 'block'; setTimeout(() => { msg.style.display = 'none'; }, 2500); }
      } catch {
        /* fallback */
        document.getElementById('reportUrlText')?.select();
        document.execCommand('copy');
      }
    });

    document.getElementById('reportClose')?.addEventListener('click', () => {
      reportModal.style.display = 'none';
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
    reportModal.addEventListener('click', (e) => { if (e.target === reportModal) reportModal.style.display = 'none'; });
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
    injectLoginUI
  };
})();
