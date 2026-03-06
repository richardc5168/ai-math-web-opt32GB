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
  function normalizeName(name){
    return String(name || '')
      .normalize('NFKC')
      .trim()
      .replace(/\s+/g, ' ')
      .toUpperCase();
  }

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

  function getAttemptTs(a){
    return Number(a && (a.ts || a.ts_end || a.timestamp) || 0);
  }

  function getTimeMs(a){
    if (a && a.time_ms) return Number(a.time_ms);
    if (a && a.time_spent_ms) return Number(a.time_spent_ms);
    const s = Number(a && a.ts_start || 0);
    const e = Number(a && a.ts_end || 0);
    if (s > 0 && e > 0 && e > s) return e - s;
    return 0;
  }

  function getMaxHint(a){
    if (a && a.max_hint != null) return Number(a.max_hint);
    if (a && a.hint && Array.isArray(a.hint.shown_levels) && a.hint.shown_levels.length)
      return Math.max.apply(null, a.hint.shown_levels);
    if (a && a.hint && a.hint.shown_count) return Math.min(3, Number(a.hint.shown_count));
    return 0;
  }

  function getTopic(a){
    return a && (a.unit_id || a.topic || a.topic_id) || '未分類';
  }

  function getModule(a){
    return a && (a.unit_id || a.module || a.moduleId || a.topic || a.topic_id) || '未分類';
  }

  function getKind(a){
    return a && (a.kind || a.template_id) || '';
  }

  function getQuestionText(a){
    if (a && a.question_text) return a.question_text;
    if (a && a.question) return a.question;
    if (a && a.extra && a.extra.question) return a.extra.question;
    return '';
  }

  function getAttemptKey(a){
    return [
      getAttemptTs(a),
      a && (a.question_id || a.qid || ''),
      getModule(a),
      getKind(a),
      (a && (a.ok || a.is_correct)) ? 1 : 0,
      String(a && (a.student_answer_raw || a.student_answer || '') || '').slice(0, 40)
    ].join('|');
  }

  function dedupeAttempts(items){
    var seen = new Set();
    var out = [];
    (Array.isArray(items) ? items : []).forEach(function(a){
      var key = getAttemptKey(a);
      if (seen.has(key)) return;
      seen.add(key);
      out.push(a);
    });
    out.sort(function(a, b){ return getAttemptTs(a) - getAttemptTs(b); });
    return out;
  }

  function normalizeAttemptForCloud(a){
    return {
      ts: getAttemptTs(a),
      ts_start: Number(a && a.ts_start || 0) || 0,
      ts_end: Number(a && a.ts_end || 0) || 0,
      question_id: String(a && (a.question_id || a.qid || '') || ''),
      ok: !!(a && (a.ok || a.is_correct)),
      is_correct: !!(a && (a.ok || a.is_correct)),
      time_ms: getTimeMs(a),
      max_hint: getMaxHint(a),
      unit_id: getModule(a),
      topic: getTopic(a),
      topic_id: String(a && a.topic_id || ''),
      kind: getKind(a),
      template_id: String(a && a.template_id || ''),
      question_text: String(getQuestionText(a) || '').slice(0, 200),
      student_answer_raw: String(a && (a.student_answer_raw || a.student_answer || '') || '').slice(0, 80),
      correct_answer: String(a && (a.correct_answer || a.answer || '') || '').slice(0, 80),
      error_type: String(a && a.error_type || ''),
      error_detail: String(a && a.error_detail || '').slice(0, 120)
    };
  }

  function collectLocalAttempts(days){
    var d = Number(days) || 7;
    var cutoff = Date.now() - d * 86400000;
    var sprintAttempts = [];
    var telAttempts = [];

    try {
      const raw = localStorage.getItem('examSprint.v1');
      if (raw) {
        const obj = safeJson(raw, null);
        if (obj && Array.isArray(obj.attempts)){
          sprintAttempts = obj.attempts.filter(function(a){ return getAttemptTs(a) >= cutoff; });
        }
      }
    } catch {}

    try {
      const uid = window.AIMathCoachLog?.getOrCreateUserId?.() || 'guest';
      telAttempts = window.AIMathAttemptTelemetry?.listAttempts?.(uid, { sinceMs: cutoff }) || [];
    } catch {}

    return dedupeAttempts([].concat(sprintAttempts, telAttempts)).map(normalizeAttemptForCloud);
  }

  function getPracticeEventsFromData(data){
    var events = data && data.d && data.d.practice && Array.isArray(data.d.practice.events)
      ? data.d.practice.events
      : [];
    return events.slice(-80);
  }

  function getStoredAttempts(entry, days){
    var cutoff = Date.now() - (Number(days) || 7) * 86400000;
    var attempts = entry && entry.data && Array.isArray(entry.data._attempts) ? entry.data._attempts : [];
    return dedupeAttempts(attempts.filter(function(a){ return getAttemptTs(a) >= cutoff; }));
  }

  function collectAliasEntries(reg, rawName){
    var entries = reg && reg.entries ? reg.entries : {};
    var nameKey = normalizeName(rawName);
    return Object.keys(entries).filter(function(k){
      var entry = entries[k] || {};
      var entryName = entry.name || k;
      return normalizeName(entryName) === nameKey || normalizeName(k) === nameKey;
    }).map(function(k){
      return { key: k, entry: entries[k] };
    });
  }

  function buildReportData(name, days, attempts, practiceEvents){
    const d = Number(days) || 7;
    const cutoff = Date.now() - d * 86400000;
    const all = dedupeAttempts((Array.isArray(attempts) ? attempts : []).filter(function(a){
      return getAttemptTs(a) >= cutoff;
    }));

    const total = all.length;
    const correct = all.filter(function(a){ return a.ok || a.is_correct; }).length;
    const accuracy = total ? Math.round(correct / total * 100) : 0;
    const totalMs = all.reduce(function(s, a){ return s + (getTimeMs(a) || 0); }, 0);
    const avgMs = total ? Math.round(totalMs / total) : 0;

    const hintDist = [0, 0, 0, 0];
    for (const a of all){
      const h = Math.max(0, Math.min(3, getMaxHint(a)));
      hintDist[h]++;
    }

    const byKey = {};
    for (const a of all){
      const topic = getTopic(a);
      const kind = getKind(a);
      const key = topic + '__' + kind;
      if (!byKey[key]) byKey[key] = { topic: topic, kind: kind, n: 0, wrong: 0, h2: 0, h3: 0 };
      byKey[key].n++;
      if (!(a.ok || a.is_correct)) byKey[key].wrong++;
      if (getMaxHint(a) >= 2) byKey[key].h2++;
      if (getMaxHint(a) >= 3) byKey[key].h3++;
    }
    const weak = Object.values(byKey)
      .map(function(x){ x.score = x.wrong * 1.0 + x.h2 * 0.25 + x.h3 * 0.25; return x; })
      .filter(function(x){ return x.wrong >= 1; })
      .sort(function(a, b){ return b.score - a.score || b.wrong - a.wrong; })
      .slice(0, 5)
      .map(function(w){ return { t: w.topic, k: w.kind, w: w.wrong, n: w.n, h2: w.h2, h3: w.h3 }; });

    const wrongList = all
      .filter(function(a){ return !(a.ok || a.is_correct); })
      .slice(-5)
      .map(function(a){
        return {
          q: String(getQuestionText(a)).substring(0, 60),
          sa: String(a.student_answer_raw || a.student_answer || '').substring(0, 20),
          ca: String(a.correct_answer || a.answer || '').substring(0, 20),
          t: getTopic(a),
          k: getKind(a),
          et: a.error_type || '',
          ed: String(a.error_detail || '').substring(0, 60)
        };
      });

    const daily = {};
    for (const a of all){
      const ts = getAttemptTs(a);
      const day = new Date(ts).toISOString().slice(0, 10);
      if (!daily[day]) daily[day] = { n: 0, ok: 0 };
      daily[day].n++;
      if (a.ok || a.is_correct) daily[day].ok++;
    }

    const byMod = {};
    for (const a of all){
      const mod = getModule(a);
      if (!byMod[mod]) byMod[mod] = { n: 0, ok: 0 };
      byMod[mod].n++;
      if (a.ok || a.is_correct) byMod[mod].ok++;
    }
    const modules = Object.entries(byMod)
      .map(function(pair){
        var m = pair[0];
        var v = pair[1];
        return { m: m, n: v.n, ok: v.ok, acc: v.n ? Math.round(v.ok / v.n * 100) : 0 };
      })
      .sort(function(a, b){ return b.n - a.n; });

    var cutoff24 = Date.now() - 86400000;
    var last24 = all.filter(function(a){ return getAttemptTs(a) >= cutoff24; });
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
      var mm = getModule(ma);
      if (!h24byMod[mm]) h24byMod[mm] = { n:0, ok:0 };
      h24byMod[mm].n++;
      if (ma.ok || ma.is_correct) h24byMod[mm].ok++;
    }
    var h24modules = Object.keys(h24byMod).map(function(k){
      var v = h24byMod[k];
      return { m:k, n:v.n, ok:v.ok, acc: v.n ? Math.round(v.ok/v.n*100) : 0 };
    }).sort(function(a,b){ return b.n - a.n; });

    var report = {
      v: 1,
      name: name,
      ts: Date.now(),
      days: d,
      d: {
        total: total,
        correct: correct,
        accuracy: accuracy,
        avgMs: avgMs,
        hintDist: hintDist,
        weak: weak,
        wrong: wrongList,
        daily: daily,
        modules: modules,
        h24: {
          total: h24total,
          correct: h24correct,
          accuracy: h24accuracy,
          avgMs: h24avgMs,
          hintDist: h24hint,
          modules: h24modules
        }
      },
      _attempts: all.slice(-600)
    };

    var practice = Array.isArray(practiceEvents) ? practiceEvents.slice(-80) : [];
    if (practice.length){
      report.d.practice = { events: practice };
    }
    return report;
  }

  /* ─── report data collector ─── */
  function collectReportData(days){
    const d = Number(days) || 7;
    const student = load();
    const name = student ? student.name : '未登入';
    return buildReportData(name, d, collectLocalAttempts(d), []);
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

  /* ─── Cloud Sync (GitHub Gist — public read, token write) ─── */
  var GIST_ID   = '9d5e5645831664954c655ca84d35e0e3';
  var GIST_PAT  = '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';
  var GIST_API  = 'https://api.github.com/gists/' + GIST_ID;
  var _cloudTimer = null;
  var _cloudInterval = null;
  var _syncInFlight = false;

  function scheduleCloudSync(){
    if (!isLoggedIn()) return;
    if (_cloudTimer) clearTimeout(_cloudTimer);
    _cloudTimer = setTimeout(doCloudSync, 3000);
  }

  /**
   * Sync report data directly into the shared Gist registry.
   * Registry structure (in registry.json): { entries: { "KAI": { pin, data, cloud_ts } } }
   */
  function doCloudSync(){
    if (!isLoggedIn()) return Promise.resolve(false);
    if (_syncInFlight) return Promise.resolve(false);
    try {
      var student = load();
      if (!student) return Promise.resolve(false);
      var nameKeyRaw = String(student.name || '').trim();
      var nameKey = normalizeName(nameKeyRaw);
      if (!nameKey) return Promise.resolve(false);
      var localAttempts = collectLocalAttempts(7);

      /* read current gist, merge, write back */
      _syncInFlight = true;
      return fetch(GIST_API, {
        headers: {
          'Accept': 'application/vnd.github+json',
          'Authorization': 'token ' + GIST_PAT
        }
      })
      .then(function(resp){
        if (!resp.ok) throw new Error('gist read ' + resp.status);
        return resp.json();
      })
      .then(function(gist){
        var content = '{}';
        try { content = gist.files['registry.json'].content; } catch(e){}
        var reg;
        try { reg = JSON.parse(content); } catch(e){ reg = {}; }
        if (!reg.entries) reg.entries = {};
        var aliases = collectAliasEntries(reg, nameKeyRaw);
        var mergedAttempts = localAttempts.slice();
        var mergedPractice = [];
        aliases.forEach(function(item){
          mergedAttempts = mergedAttempts.concat(getStoredAttempts(item.entry, 7));
          mergedPractice = mergedPractice.concat(getPracticeEventsFromData(item.entry && item.entry.data));
        });
        mergedAttempts = dedupeAttempts(mergedAttempts).slice(-600);
        mergedPractice = mergedPractice.slice(-80);
        var reportData = buildReportData(nameKeyRaw, 7, mergedAttempts, mergedPractice);
        var entry = {
          name: nameKeyRaw,
          pin: student.pin || '',
          data: reportData,
          cloud_ts: Date.now()
        };
        aliases.forEach(function(item){
          if (item.key !== nameKey) delete reg.entries[item.key];
        });
        reg.entries[nameKey] = entry;
        reg._r = 'v1';
        return fetch(GIST_API, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github+json',
            'Authorization': 'token ' + GIST_PAT
          },
          body: JSON.stringify({
            files: { 'registry.json': { content: JSON.stringify(reg) } }
          })
        });
      })
      .then(function(resp){
        if (resp && resp.ok){
          console.log('[cloud-sync] OK');
          return true;
        }
        return false;
      })
      .catch(function(e){ console.warn('[cloud-sync] fail', e); return false; })
      .finally(function(){ _syncInFlight = false; });
    } catch(e){
      return Promise.resolve(false);
    }
  }

  /**
   * Look up a student's report from the public Gist registry.
   * Returns { pin, data, cloud_ts } or null.
   */
  function lookupStudentReport(name){
    var raw = String(name || '').trim();
    var nameKey = normalizeName(raw);
    if (!nameKey) return Promise.resolve(null);
    /* public gist — no auth required, has CORS */
    return fetch(GIST_API, {
      headers: { 'Accept': 'application/vnd.github+json' }
    })
    .then(function(resp){
      if (!resp.ok) return null;
      return resp.json();
    })
    .then(function(gist){
      if (!gist || !gist.files || !gist.files['registry.json']) return null;
      var reg;
      try { reg = JSON.parse(gist.files['registry.json'].content); } catch(e){ return null; }
      if (!reg || !reg.entries) return null;
      var aliases = collectAliasEntries(reg, raw);
      if (!aliases.length) return null;
      aliases.sort(function(a, b){
        return Number((b.entry && b.entry.cloud_ts) || 0) - Number((a.entry && a.entry.cloud_ts) || 0);
      });
      var mergedAttempts = [];
      var mergedPractice = [];
      aliases.forEach(function(item){
        mergedAttempts = mergedAttempts.concat(getStoredAttempts(item.entry, 7));
        mergedPractice = mergedPractice.concat(getPracticeEventsFromData(item.entry && item.entry.data));
      });
      if (mergedAttempts.length){
        var latest = aliases[0].entry || {};
        return {
          name: latest.name || raw,
          pin: latest.pin || '',
          data: buildReportData(latest.name || raw, 7, mergedAttempts, mergedPractice),
          cloud_ts: latest.cloud_ts || 0
        };
      }
      return aliases[0].entry || null;
    })
    .catch(function(){ return null; });
  }

  function recordPracticeResult(name, result){
    var nameKey = normalizeName(name);
    if (!nameKey) return Promise.resolve(false);
    var score = Math.max(0, Number(result && result.score || 0));
    var total = Math.max(1, Number(result && result.total || 1));
    var event = {
      ts: Date.now(),
      score: score,
      total: total,
      topic: String(result && result.topic || ''),
      kind: String(result && result.kind || ''),
      mode: String(result && result.mode || 'quiz')
    };
    return fetch(GIST_API, {
      headers: {
        'Accept': 'application/vnd.github+json',
        'Authorization': 'token ' + GIST_PAT
      }
    })
    .then(function(resp){
      if (!resp.ok) throw new Error('gist read ' + resp.status);
      return resp.json();
    })
    .then(function(gist){
      var content = '{}';
      try { content = gist.files['registry.json'].content; } catch(e){}
      var reg;
      try { reg = JSON.parse(content); } catch(e){ reg = {}; }
      if (!reg.entries) reg.entries = {};
      var entry = reg.entries[nameKey] || { pin: '', cloud_ts: Date.now(), data: { v:1, name: name || '', ts: Date.now(), days:7, d:{} } };
      if (!entry.data) entry.data = { v:1, name: name || '', ts: Date.now(), days:7, d:{} };
      if (!entry.data.d) entry.data.d = {};
      if (!entry.data.d.practice) entry.data.d.practice = { events: [] };
      if (!Array.isArray(entry.data.d.practice.events)) entry.data.d.practice.events = [];
      entry.data.d.practice.events.push(event);
      if (entry.data.d.practice.events.length > 80){
        entry.data.d.practice.events = entry.data.d.practice.events.slice(-80);
      }
      entry.cloud_ts = Date.now();
      reg.entries[nameKey] = entry;
      reg._r = 'v1';
      return fetch(GIST_API, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/vnd.github+json',
          'Authorization': 'token ' + GIST_PAT
        },
        body: JSON.stringify({
          files: { 'registry.json': { content: JSON.stringify(reg) } }
        })
      });
    })
    .then(function(resp){ return !!(resp && resp.ok); })
    .catch(function(){ return false; });
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
      if (!_cloudInterval){
        _cloudInterval = setInterval(scheduleCloudSync, 20000);
      }
      window.addEventListener('visibilitychange', function(){
        if (document.visibilityState === 'hidden') doCloudSync();
      });
      window.addEventListener('beforeunload', doCloudSync);
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
    forceCloudSync: doCloudSync,
    lookupStudentReport,
    recordPracticeResult
  };
})();
