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
  function safeJson(s, fb){ try { return JSON.parse(s); } catch(e) { return fb; } }
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
    } catch(e) {}
    return null;
  }

  function save(o){
    try { localStorage.setItem(LS_KEY, JSON.stringify(o)); } catch(e) {}
  }

  /* ─── public API ─── */
  function isLoggedIn(){
    return !!load();
  }

  function getCurrentStudent(){
    return load();
  }

  function patchCurrentStudent(patch){
    const current = load();
    if (!current) return null;
    const next = Object.assign({}, current, patch || {}, { updated_at: nowIso() });
    save(next);
    return next;
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
    try { localStorage.removeItem(LS_KEY); } catch(e) {}
  }

  function verifyPin(input){
    const s = load();
    if (!s) return false;
    return String(input || '').trim() === s.pin;
  }

  function parseAttemptTs(value){
    var num = Number(value);
    if (isFinite(num) && num > 0) return num;
    var parsed = Date.parse(String(value || ''));
    return isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function getAttemptTs(a){
    if (!a) return 0;
    return parseAttemptTs(
      a.ts ||
      a.ts_end ||
      a.timestamp ||
      a.answeredAt ||
      a.submittedAt ||
      a.createdAt
    );
  }

  function isAttemptCorrect(a){
    return !!(a && (a.ok || a.is_correct));
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
    var ts = getAttemptTs(a);
    var extra = (a && a.extra && typeof a.extra === 'object') ? a.extra : {};
    var hint = (a && a.hint && typeof a.hint === 'object') ? a.hint : {};
    var out = {
      ts: ts,
      answeredAt: ts ? new Date(ts).toISOString() : '',
      ts_start: Number(a && a.ts_start || 0) || 0,
      ts_end: Number(a && a.ts_end || 0) || 0,
      question_id: String(a && (a.question_id || a.qid || '') || ''),
      ok: isAttemptCorrect(a),
      is_correct: isAttemptCorrect(a),
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
    /* R48: preserve hint evidence chain fields for cloud analytics */
    var hs = extra.hint_sequence || hint.hint_sequence;
    var ht = extra.hint_open_ts || hint.hint_open_ts;
    var hl = extra.hint_level_used != null ? extra.hint_level_used : hint.hint_level_used;
    if (Array.isArray(hs) && hs.length > 0) out.hint_sequence = hs;
    if (Array.isArray(ht) && ht.length > 0) out.hint_open_ts = ht;
    if (hl != null) out.hint_level_used = Number(hl);
    return out;
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
    } catch(e) {}

    try {
      const uid = (window.AIMathCoachLog && window.AIMathCoachLog.getOrCreateUserId) ? window.AIMathCoachLog.getOrCreateUserId() : 'guest';
      telAttempts = (window.AIMathAttemptTelemetry && window.AIMathAttemptTelemetry.listAttempts) ? window.AIMathAttemptTelemetry.listAttempts(uid, { sinceMs: cutoff }) : [];
    } catch(e) {}

    return dedupeAttempts([].concat(sprintAttempts, telAttempts)).map(normalizeAttemptForCloud);
  }



  function tryBuildReportDataWithShared(name, days, attempts, practiceEvents){
    var builder = window.AIMathReportDataBuilder;
    if (!builder || typeof builder.buildReportData !== 'function') return null;
    return builder.buildReportData({
      name: name,
      days: days,
      attempts: attempts,
      practiceEvents: practiceEvents
    });
  }

  function buildReportData(name, days, attempts, practiceEvents){
    var sharedResult = tryBuildReportDataWithShared(name, days, attempts, practiceEvents);
    if (sharedResult) return sharedResult;

    const d = Number(days) || 7;
    const cutoff = Date.now() - d * 86400000;
    const all = dedupeAttempts((Array.isArray(attempts) ? attempts : []).filter(function(a){
      return getAttemptTs(a) >= cutoff;
    }));

    const total = all.length;
    const correct = all.filter(isAttemptCorrect).length;
    const incorrect = total - correct;
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
      if (!isAttemptCorrect(a)) byKey[key].wrong++;
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
      .filter(function(a){ return !isAttemptCorrect(a); })
      .sort(function(a, b){ return getAttemptTs(b) - getAttemptTs(a); })
      .slice(0, 5)
      .map(function(a){
        var ts = getAttemptTs(a);
        return {
          ts: ts,
          answeredAt: ts ? new Date(ts).toISOString() : '',
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
      if (isAttemptCorrect(a)) daily[day].ok++;
    }

    const byMod = {};
    for (const a of all){
      const mod = getModule(a);
      if (!byMod[mod]) byMod[mod] = { n: 0, ok: 0 };
      byMod[mod].n++;
      if (isAttemptCorrect(a)) byMod[mod].ok++;
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
    var h24correct = last24.filter(isAttemptCorrect).length;
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
      if (isAttemptCorrect(ma)) h24byMod[mm].ok++;
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
        incorrect: incorrect,
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
    } catch(e) { return null; }
  }

  /* ─── Cloud Sync (Backend registry) ─── */
  var PARENT_REPORT_API_BASE_KEY = 'aimath_parent_report_api_base_v1';
  var _cloudTimer = null;
  var _cloudInterval = null;
  var _apiBaseProbePromise = null;
  var _syncInFlight = false;
  var _cloudBackendWarned = false;
  var _cloudPinWarned = false;

  function normalizeApiBase(base){
    return String(base || '').trim().replace(/\/+$/, '');
  }

  function getStoredParentReportApiBase(){
    var fromWindow = normalizeApiBase(window.AIMATH_PARENT_REPORT_API_BASE || window.AIMATH_API_BASE || '');
    if (fromWindow) return fromWindow;
    try {
      var params = new URLSearchParams(window.location.search || '');
      var fromQuery = normalizeApiBase(params.get('api') || '');
      if (fromQuery) {
        try { localStorage.setItem(PARENT_REPORT_API_BASE_KEY, fromQuery); } catch(e) {}
        return fromQuery;
      }
    } catch(e) {}
    try {
      return normalizeApiBase(localStorage.getItem(PARENT_REPORT_API_BASE_KEY) || '');
    } catch(e) {
      return '';
    }
  }

  function getSameOriginParentReportApiBase(){
    try {
      var origin = normalizeApiBase(window.location.origin || '');
      var protocol = String(window.location.protocol || '').toLowerCase();
      var host = String(window.location.hostname || '').toLowerCase();
      if (!origin || protocol.indexOf('http') !== 0) return '';
      if (host === 'localhost' || host === '127.0.0.1') return origin;
      if (host.indexOf('github.io') !== -1) return '';
      return origin;
    } catch(e) {
      return '';
    }
  }

  function getBackendConfigUrls(){
    try {
      var host = String(window.location.hostname || '').toLowerCase();
      var path = String(window.location.pathname || '/');
      var parts = path.split('/').filter(Boolean);
      var urls = ['/backend-config.json'];
      if (host.indexOf('github.io') !== -1 && parts.length) {
        urls.unshift('/' + parts[0] + '/backend-config.json');
      }
      return urls.filter(function(url, idx, arr){ return arr.indexOf(url) === idx; });
    } catch(e) {
      return ['/backend-config.json'];
    }
  }

  function notifyParentReportApiBaseReady(base, source){
    var normalized = normalizeApiBase(base);
    if (!normalized) return;
    try {
      window.dispatchEvent(new CustomEvent('aimath:backend-base-ready', {
        detail: { base: normalized, source: String(source || 'auto') }
      }));
    } catch(e) {}
  }

  function rememberParentReportApiBase(base, source){
    var normalized = normalizeApiBase(base);
    if (!normalized) return false;
    try {
      localStorage.setItem(PARENT_REPORT_API_BASE_KEY, normalized);
      notifyParentReportApiBaseReady(normalized, source || 'stored');
      return true;
    } catch(e) {
      return false;
    }
  }

  function detectParentReportApiBase(){
    var existing = getStoredParentReportApiBase() || getSameOriginParentReportApiBase();
    if (existing) {
      notifyParentReportApiBaseReady(existing, 'existing');
      return Promise.resolve(existing);
    }
    if (_apiBaseProbePromise) return _apiBaseProbePromise;
    _apiBaseProbePromise = getBackendConfigUrls().reduce(function(chain, url){
      return chain.then(function(found){
        if (found) return found;
        return fetch(url, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        })
        .then(function(resp){
          if (!resp.ok) return '';
          return resp.json().then(function(body){
            return normalizeApiBase(body && body.api_base || '');
          }).catch(function(){ return ''; });
        })
        .catch(function(){ return ''; });
      });
    }, Promise.resolve(''))
    .then(function(found){
      if (found) rememberParentReportApiBase(found, 'backend-config');
      return found;
    })
    .catch(function(){ return ''; })
    .finally(function(){ _apiBaseProbePromise = null; });
    return _apiBaseProbePromise;
  }

  function getParentReportApiBase(){
    return getStoredParentReportApiBase() || getSameOriginParentReportApiBase();
  }

  function setParentReportApiBase(base){
    var normalized = normalizeApiBase(base);
    try {
      if (!normalized) {
        localStorage.removeItem(PARENT_REPORT_API_BASE_KEY);
        return false;
      }
      localStorage.setItem(PARENT_REPORT_API_BASE_KEY, normalized);
      notifyParentReportApiBaseReady(normalized, 'manual');
      return true;
    } catch(e) {
      return false;
    }
  }

  function clearParentReportApiBase(){
    try { localStorage.removeItem(PARENT_REPORT_API_BASE_KEY); } catch(e) {}
  }

  function hasParentReportApiBase(){
    return !!getParentReportApiBase();
  }

  function buildParentReportApiUrl(path){
    var base = getParentReportApiBase();
    if (!base) return '';
    return base + path;
  }

  function postParentReportApi(path, payload){
    var url = buildParentReportApiUrl(path);
    if (!url) return Promise.resolve({ ok: false, error: 'missing_backend' });
    return fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload || {})
    })
    .then(function(resp){
      return resp.text().then(function(text){
        var body = null;
        try { body = text ? JSON.parse(text) : null; } catch(e) {}
        return {
          ok: resp.ok,
          status: resp.status,
          body: body
        };
      });
    })
    .catch(function(err){
      return { ok: false, error: 'network', detail: err };
    });
  }

  function warnMissingCloudBackend(){
    if (_cloudBackendWarned) return;
    _cloudBackendWarned = true;
    console.warn('[cloud-sync] write disabled: missing AIMATH_PARENT_REPORT_API_BASE backend');
  }

  function warnMissingCloudPin(){
    if (_cloudPinWarned) return;
    _cloudPinWarned = true;
    console.warn('[cloud-sync] write disabled: missing parent-report PIN for backend sync');
  }

  function resolveParentReportPin(name, pinOverride){
    var direct = String(pinOverride || '').trim();
    if (/^\d{4,6}$/.test(direct)) return direct;
    var current = load();
    if (!current) return '';
    if (normalizeName(current.name) !== normalizeName(name)) return '';
    return /^\d{4,6}$/.test(String(current.pin || '').trim()) ? String(current.pin || '').trim() : '';
  }

  function scheduleCloudSync(){
    if (!isLoggedIn()) return;
    if (_cloudTimer) clearTimeout(_cloudTimer);
    _cloudTimer = setTimeout(doCloudSync, 3000);
  }

  /**
   * Sync report data to the backend registry.
   */
  function doCloudSync(){
    if (!isLoggedIn()) return Promise.resolve(false);
    if (_syncInFlight) return Promise.resolve(false);
    if (!hasParentReportApiBase()) {
      return detectParentReportApiBase().then(function(base){
        if (!base) {
          warnMissingCloudBackend();
          return false;
        }
        return doCloudSync();
      });
    }
    try {
      var student = load();
      if (!student) return Promise.resolve(false);
      var nameKeyRaw = String(student.name || '').trim();
      var nameKey = normalizeName(nameKeyRaw);
      if (!nameKey) return Promise.resolve(false);
      var pin = resolveParentReportPin(nameKeyRaw, student.pin);
      if (!pin) {
        warnMissingCloudPin();
        return Promise.resolve(false);
      }
      var localAttempts = collectLocalAttempts(7);
      var reportData = buildReportData(nameKeyRaw, 7, localAttempts, []);

      _syncInFlight = true;
      return postParentReportApi('/v1/parent-report/registry/upsert', {
        name: nameKeyRaw,
        pin: pin,
        report_data: reportData
      })
      .then(function(resp){
        if (resp && resp.ok){
          console.log('[cloud-sync] OK');
          return true;
        }
        console.warn('[cloud-sync] backend write fail', resp && (resp.body || resp));
        return false;
      })
      .catch(function(e){ console.warn('[cloud-sync] fail', e); return false; })
      .finally(function(){ _syncInFlight = false; });
    } catch(e){
      return Promise.resolve(false);
    }
  }

  /**
   * Look up a student's report from the backend registry.
   * Returns { data, cloud_ts } or error object, or null.
   */
  function lookupStudentReport(name, pin){
    var raw = String(name || '').trim();
    var nameKey = normalizeName(raw);
    if (!nameKey) return Promise.resolve(null);
    var resolvedPin = String(pin || '').trim();
    if (!hasParentReportApiBase()) {
      return detectParentReportApiBase().then(function(base){
        if (!base) return null;
        return lookupStudentReport(name, pin);
      });
    }
    if (hasParentReportApiBase() && /^\d{4,6}$/.test(resolvedPin)) {
      return postParentReportApi('/v1/parent-report/registry/fetch', {
        name: raw,
        pin: resolvedPin
      })
      .then(function(resp){
        if (resp && resp.ok && resp.body && resp.body.entry) return resp.body.entry;
        if (resp && resp.status === 403) return { error: 'invalid_pin' };
        if (resp && resp.status === 404) return { error: 'not_found' };
        if (resp && resp.error === 'network') return { error: 'network' };
        return null;
      });
    }
    return Promise.resolve(null);
  }

  function recordPracticeResult(name, result, pinOverride){
    var nameKey = normalizeName(name);
    if (!nameKey) return Promise.resolve(false);
    if (!hasParentReportApiBase()) {
      return detectParentReportApiBase().then(function(base){
        if (!base) {
          warnMissingCloudBackend();
          return false;
        }
        return recordPracticeResult(name, result, pinOverride);
      });
    }
    var pin = resolveParentReportPin(name, pinOverride);
    if (!pin) {
      warnMissingCloudPin();
      return Promise.resolve(false);
    }
    var score = Math.max(0, Number(result && result.score || 0));
    var total = Math.max(1, Number(result && result.total || 1));
    var event = {
      ts: Date.now(),
      score: score,
      total: total,
      topic: String(result && result.topic || ''),
      kind: String(result && result.kind || ''),
      mode: String(result && result.mode || 'quiz'),
      completed: !(result && result.completed === false)
    };
    /* R48: forward hint evidence chain fields if present */
    if (result && Array.isArray(result.hint_sequence) && result.hint_sequence.length > 0) event.hint_sequence = result.hint_sequence;
    if (result && Array.isArray(result.hint_open_ts) && result.hint_open_ts.length > 0) event.hint_open_ts = result.hint_open_ts;
    if (result && result.hint_level_used != null) event.hint_level_used = Number(result.hint_level_used);
    return postParentReportApi('/v1/parent-report/registry/upsert', {
      name: String(name || '').trim(),
      pin: pin,
      practice_event: event
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

    detectParentReportApiBase();

    const student = load();

    function buildParentReportLink(baseHref){
      var href = String(baseHref || '../parent-report/');
      var apiBase = getParentReportApiBase();
      if (!apiBase) return href;
      return href + (href.indexOf('?') >= 0 ? '&' : '?') + 'api=' + encodeURIComponent(apiBase);
    }

    function getCloudStatusMeta(){
      var apiBase = getParentReportApiBase();
      if (apiBase) {
        return {
          text: '☁️ 雲端同步已連線',
          color: 'var(--ok,#2ea043)'
        };
      }
      return {
        text: '☁️ 目前僅本機保存',
        color: 'var(--warn,#d29922)'
      };
    }

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

    var reportLink = buildParentReportLink(parentReportHref);
    var cloudStatus = getCloudStatusMeta();

    if (student){
      wrapper.innerHTML = `
        <span style="font-size:13px;color:var(--muted,#9aa4b2)">👤 <strong style="color:var(--text,#e6edf3)">${escHtml(student.name)}</strong></span>
        <span id="studentCloudState" style="font-size:11px;color:${cloudStatus.color}">${cloudStatus.text}</span>
        <a href="${reportLink}" id="btnParentReport" style="text-decoration:none"><button class="btn ghost" style="font-size:12px;padding:6px 10px" type="button">📊 家長報告</button></a>
        <button class="btn ghost" id="btnLogout" style="font-size:12px;padding:6px 10px">登出</button>
      `;
    } else {
      wrapper.innerHTML = `
        <button class="btn" id="btnLoginShow" style="font-size:12px;padding:6px 10px">🔑 學生登入</button>
        <span id="studentCloudState" style="font-size:11px;color:${cloudStatus.color}">${cloudStatus.text}</span>
        <span id="studentCloudHint" style="font-size:11px;color:var(--muted,#9aa4b2)">登入後可查看家長報告</span>
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

    function refreshCloudUi(){
      var meta = getCloudStatusMeta();
      var stateEl = document.getElementById('studentCloudState');
      if (stateEl) {
        stateEl.textContent = meta.text;
        stateEl.style.color = meta.color;
      }
      var hintEl = document.getElementById('studentCloudHint');
      if (hintEl && !getParentReportApiBase()) {
        hintEl.textContent = '登入後可查看家長報告；若未連線雲端，跨裝置不會同步';
      }
      var reportEl = document.getElementById('btnParentReport');
      if (reportEl) reportEl.href = buildParentReportLink(parentReportHref);
    }

    window.addEventListener('aimath:backend-base-ready', refreshCloudUi);
    detectParentReportApiBase().then(function(){ refreshCloudUi(); });
    refreshCloudUi();



    /* event handlers */
    const btnLogin = document.getElementById('btnLoginShow');
    const btnLogout = document.getElementById('btnLogout');

    if (btnLogin){
      btnLogin.addEventListener('click', function(){
        modal.style.display = 'flex';
        var nameEl = document.getElementById('authName');
        if (nameEl) nameEl.focus();
      });
    }

    if (btnLogout){
      btnLogout.addEventListener('click', function(){
        if (confirm('確定登出？（作答紀錄仍保留在本機）')) {
          logout();
          location.reload();
        }
      });
    }

    var submitEl = document.getElementById('authSubmit');
    if (submitEl) submitEl.addEventListener('click', function(){
      var errEl = document.getElementById('authError');
      try {
        var nameEl2 = document.getElementById('authName');
        var pinEl2 = document.getElementById('authPin');
        var name = nameEl2 ? nameEl2.value : '';
        var pin = pinEl2 ? pinEl2.value : '';
        login(name, pin);
        modal.style.display = 'none';
        location.reload();
      } catch (e) {
        if (errEl){ errEl.textContent = e.message; errEl.style.display = 'block'; }
      }
    });

    var cancelEl = document.getElementById('authCancel');
    if (cancelEl) cancelEl.addEventListener('click', function(){
      modal.style.display = 'none';
    });

    /* Enter key in modal */
    var pinEl3 = document.getElementById('authPin');
    if (pinEl3) pinEl3.addEventListener('keydown', function(e){
      if (e.key === 'Enter') { var s = document.getElementById('authSubmit'); if (s) s.click(); }
    });
    var nameEl3 = document.getElementById('authName');
    if (nameEl3) nameEl3.addEventListener('keydown', function(e){
      if (e.key === 'Enter') { var p = document.getElementById('authPin'); if (p) p.focus(); }
    });

    /* Click outside to close */
    modal.addEventListener('click', function(e){ if (e.target === modal) modal.style.display = 'none'; });

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
    patchCurrentStudent,
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
    recordPracticeResult,
    getParentReportApiBase,
    detectParentReportApiBase,
    setParentReportApiBase,
    clearParentReportApiBase
  };
})();
