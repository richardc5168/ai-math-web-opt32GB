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
    try { return JSON.parse(s); } catch { return fallback; }
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
    } catch {}
    return { version: VERSION, user_id: String(userId || 'guest'), attempts: [] };
  }

  function saveLog(userId, log){
    try {
      localStorage.setItem(keyForUser(userId), JSON.stringify(log));
      return true;
    } catch {
      return false;
    }
  }

  function appendAttempt(userId, attemptEvent, opts){
    const log = loadLog(userId);
    log.user_id = String(userId || 'guest');

    const maxN = Math.max(100, Number(opts?.maxAttempts || 5000));
    log.attempts.push(attemptEvent);
    if (log.attempts.length > maxN){
      log.attempts.splice(0, log.attempts.length - maxN);
    }

    const ok = saveLog(userId, log);
    return { ok, size: log.attempts.length };
  }

  function listAttempts(userId, opts){
    const log = loadLog(userId);
    const sinceMs = opts?.sinceMs != null ? Number(opts.sinceMs) : null;
    const limit = opts?.limit != null ? Math.max(1, Number(opts.limit)) : null;

    let items = log.attempts || [];
    if (Number.isFinite(sinceMs)){
      items = items.filter(x => Number(x?.ts_end) >= sinceMs);
    }
    if (Number.isFinite(limit)){
      items = items.slice(-limit);
    }
    return items.slice();
  }

  function clearAttempts(userId){
    try { localStorage.removeItem(keyForUser(userId)); } catch {}
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
