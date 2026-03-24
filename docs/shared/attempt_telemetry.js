/*
  AIMathAttemptTelemetry (frontend)
  - AttemptEvent (question-level) append-only telemetry.
  - Persists to localStorage.
  - Intended for Coach Mode + weekly parent report.

  Storage:
    key = ai_math_attempts_v1::<user_id>
    value = { version: 1, user_id, attempts: AttemptEvent[] }
*/

(function(){
  'use strict';

  const VERSION = 1;

  function safeJsonParse(s, fallback){
    try { return JSON.parse(s); } catch(e) { return fallback; }
  }

  function keyForUser(userId){
    const uid = String(userId || '').trim() || 'guest';
    return `ai_math_attempts_v1::${uid}`;
  }

  function loadLog(userId){
    const key = keyForUser(userId);
    try {
      const raw = localStorage.getItem(key);
      const obj = raw ? safeJsonParse(raw, null) : null;
      if (obj && obj.version === VERSION && Array.isArray(obj.attempts)) return obj;
    } catch(e) {}
    return { version: VERSION, user_id: String(userId || 'guest'), attempts: [] };
  }

  function saveLog(userId, log){
    try {
      localStorage.setItem(keyForUser(userId), JSON.stringify(log));
      return true;
    } catch(e) {
      return false;
    }
  }

  function getSharedHintTrace(){
    if (!window.AIMathHintEngine || typeof window.AIMathHintEngine.getHintTrace !== 'function') {
      return null;
    }
    try {
      return window.AIMathHintEngine.getHintTrace();
    } catch(e) {
      return null;
    }
  }

  function normalizeAttemptEvent(attemptEvent){
    const evt = Object.assign({}, attemptEvent || {});
    evt.hint = Object.assign({}, evt.hint || {});
    evt.extra = Object.assign({}, evt.extra || {});

    const trace = getSharedHintTrace();
    const hintSequence = Array.isArray(evt.hint.hint_sequence) && evt.hint.hint_sequence.length > 0
      ? evt.hint.hint_sequence.slice()
      : (trace && Array.isArray(trace.hint_sequence) ? trace.hint_sequence.slice() : []);
    const hintOpenTs = Array.isArray(evt.hint.hint_open_ts) && evt.hint.hint_open_ts.length > 0
      ? evt.hint.hint_open_ts.slice()
      : (trace && Array.isArray(trace.hint_open_ts) ? trace.hint_open_ts.slice() : []);

    if (hintSequence.length > 0) evt.hint.hint_sequence = hintSequence;
    if (hintOpenTs.length > 0) evt.hint.hint_open_ts = hintOpenTs;

    const hintLevelUsed = Number.isFinite(Number(evt.hint.hint_level_used))
      ? Math.max(0, Number(evt.hint.hint_level_used))
      : (trace ? Math.max(0, Number(trace.hint_level_used || 0)) : 0);

    if (hintLevelUsed > 0) evt.hint.hint_level_used = hintLevelUsed;
    if (!Number.isFinite(Number(evt.hint.shown_count)) && hintSequence.length > 0) {
      evt.hint.shown_count = hintSequence.length;
    }

    if (hintSequence.length > 0 && evt.extra.hint_sequence == null) evt.extra.hint_sequence = hintSequence.slice();
    if (hintOpenTs.length > 0 && evt.extra.hint_open_ts == null) evt.extra.hint_open_ts = hintOpenTs.slice();
    if (hintLevelUsed > 0 && evt.extra.hint_level_used == null) evt.extra.hint_level_used = hintLevelUsed;

    return evt;
  }

  function appendAttempt(userId, attemptEvent, opts){
    const log = loadLog(userId);
    log.user_id = String(userId || 'guest');
    const normalizedAttemptEvent = normalizeAttemptEvent(attemptEvent);

    const maxN = Math.max(100, Number((opts && opts.maxAttempts) || 5000));
    log.attempts.push(normalizedAttemptEvent);
    if (log.attempts.length > maxN){
      log.attempts.splice(0, log.attempts.length - maxN);
    }

    const ok = saveLog(userId, log);

    // Bridge to AIMathAnalytics if available
    if (window.AIMathAnalytics && typeof window.AIMathAnalytics.track === 'function'){
      try {
        var evName = normalizedAttemptEvent.is_correct ? 'question_correct' : 'question_submit';
        window.AIMathAnalytics.track(evName, {
          unit_id: normalizedAttemptEvent.unit_id,
          question_id: normalizedAttemptEvent.question_id,
          kind: normalizedAttemptEvent.kind,
          topic_id: normalizedAttemptEvent.topic_id || '',
          is_correct: normalizedAttemptEvent.is_correct,
          attempts_count: normalizedAttemptEvent.attempts_count,
          hint_shown: normalizedAttemptEvent.hint ? normalizedAttemptEvent.hint.shown_count : 0,
          time_ms: normalizedAttemptEvent.time_ms || 0,
          error_type: normalizedAttemptEvent.error_type || ''
        });
        if (normalizedAttemptEvent.hint && normalizedAttemptEvent.hint.shown_count > 0){
          window.AIMathAnalytics.track('hint_open', {
            unit_id: normalizedAttemptEvent.unit_id,
            question_id: normalizedAttemptEvent.question_id,
            topic_id: normalizedAttemptEvent.topic_id || '',
            levels: normalizedAttemptEvent.hint.shown_levels,
            hint_sequence: normalizedAttemptEvent.hint.hint_sequence || [],
            hint_open_ts: normalizedAttemptEvent.hint.hint_open_ts || []
          });
        }
      } catch(e){}
    }

    return { ok, size: log.attempts.length };
  }

  function listAttempts(userId, opts){
    const log = loadLog(userId);
    const sinceMs = (opts && opts.sinceMs != null) ? Number(opts.sinceMs) : null;
    const limit = (opts && opts.limit != null) ? Math.max(1, Number(opts.limit)) : null;

    let items = log.attempts || [];
    if (Number.isFinite(sinceMs)){
      items = items.filter(x => Number(x && x.ts_end) >= sinceMs);
    }
    if (Number.isFinite(limit)){
      items = items.slice(-limit);
    }
    return items.slice();
  }

  function clearAttempts(userId){
    try { localStorage.removeItem(keyForUser(userId)); } catch(e) {}
  }

  function exportAttemptsJson(userId){
    const log = loadLog(userId);
    return JSON.stringify(log, null, 2);
  }

  window.AIMathAttemptTelemetry = {
    VERSION,
    keyForUser,
    loadLog,
    appendAttempt,
    listAttempts,
    clearAttempts,
    exportAttemptsJson,
  };
})();
