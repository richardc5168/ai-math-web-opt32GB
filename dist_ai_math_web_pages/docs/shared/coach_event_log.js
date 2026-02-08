/*
  AIMathCoachLog (frontend)
  - Coach Mode event logger.
  - Persists to localStorage.
  - Designed to be embedded in GitHub Pages static modules.

  Key requirement:
  - Coach Mode should allow continuing to next question even if the answer is wrong.
    This module supports logging that via `allow_continue: true`.
*/

(function(){
  'use strict';

  const USER_ID_KEY = 'aimath_coach_user_id_v1';
  const EVENTS_KEY = 'aimath_coach_events_v1';
  const DB_VERSION = 1;

  const EventType = {
    ATTEMPT_STARTED: 'attempt_started',
    HINT_SHOWN: 'hint_shown',
    ANSWER_SUBMITTED: 'answer_submitted',
    ATTEMPT_COMPLETED: 'attempt_completed',
    NEXT_QUESTION: 'next_question',
  };

  function nowMs(){ return Date.now(); }

  function safeJsonParse(s, fallback){
    try { return JSON.parse(s); } catch { return fallback; }
  }

  function randomHex(nBytes){
    const bytes = new Uint8Array(nBytes);
    if (typeof crypto !== 'undefined' && crypto.getRandomValues){
      crypto.getRandomValues(bytes);
    } else {
      for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
    }
    return Array.from(bytes).map(b => b.toString(16).padStart(2,'0')).join('');
  }

  // UUID-ish string (not strict RFC4122, but stable enough for local user id)
  function newUserId(){
    const a = randomHex(4);
    const b = randomHex(2);
    const c = randomHex(2);
    const d = randomHex(2);
    const e = randomHex(6);
    return `u_${a}-${b}-${c}-${d}-${e}`;
  }

  function getOrCreateUserId(){
    try {
      const cur = localStorage.getItem(USER_ID_KEY);
      if (cur && String(cur).trim()) return String(cur);
      const uid = newUserId();
      localStorage.setItem(USER_ID_KEY, uid);
      return uid;
    } catch {
      return 'guest';
    }
  }

  function loadDb(){
    const raw = (function(){
      try { return localStorage.getItem(EVENTS_KEY); } catch { return null; }
    })();

    const db = raw ? safeJsonParse(raw, null) : null;
    if (db && typeof db === 'object' && db.version === DB_VERSION && Array.isArray(db.events)){
      if (!db.user_id) db.user_id = getOrCreateUserId();
      return db;
    }

    return { version: DB_VERSION, user_id: getOrCreateUserId(), events: [] };
  }

  function saveDb(db){
    try { localStorage.setItem(EVENTS_KEY, JSON.stringify(db)); } catch {}
  }

  function normalizeEvent(evt){
    const e = evt && typeof evt === 'object' ? Object.assign({}, evt) : {};
    e.type = String(e.type || '').trim();
    e.ts_ms = Number.isFinite(Number(e.ts_ms)) ? Number(e.ts_ms) : nowMs();
    if (e.question_id != null) e.question_id = String(e.question_id);
    if (e.unit != null) e.unit = String(e.unit);
    if (e.app_id != null) e.app_id = String(e.app_id);
    if (e.hint_level != null) e.hint_level = Number(e.hint_level);
    if (e.correct != null) e.correct = !!e.correct;
    if (e.allow_continue != null) e.allow_continue = !!e.allow_continue;
    if (e.payload != null && typeof e.payload !== 'object') e.payload = { value: e.payload };
    if (!e.payload) e.payload = {};
    return e;
  }

  function appendEvent(evt, opts){
    const db = loadDb();
    const maxEvents = Math.max(50, Number(opts?.maxEvents || 2000));

    const e = normalizeEvent(evt);
    if (!e.type) return { ok: false, reason: 'missing type' };

    db.events.push(e);
    if (db.events.length > maxEvents){
      db.events.splice(0, db.events.length - maxEvents);
    }

    saveDb(db);
    return { ok: true, user_id: db.user_id, size: db.events.length };
  }

  function listEvents(opts){
    const db = loadDb();
    const sinceMs = opts?.sinceMs != null ? Number(opts.sinceMs) : null;
    const limit = opts?.limit != null ? Math.max(1, Number(opts.limit)) : null;

    let evts = db.events;
    if (Number.isFinite(sinceMs)){
      evts = evts.filter(e => Number(e?.ts_ms) >= sinceMs);
    }
    if (Number.isFinite(limit)){
      evts = evts.slice(-limit);
    }

    return { user_id: db.user_id, events: evts.slice() };
  }

  function exportEventsJson(){
    const db = loadDb();
    return JSON.stringify(db, null, 2);
  }

  function clearEvents(){
    const db = { version: DB_VERSION, user_id: getOrCreateUserId(), events: [] };
    saveDb(db);
    return { ok: true };
  }

  // Coach policy helper: in Coach Mode, always allow continuing.
  function allowContinueAlways(){ return true; }

  window.AIMathCoachLog = {
    EventType,
    getOrCreateUserId,
    appendEvent,
    listEvents,
    exportEventsJson,
    clearEvents,
    allowContinueAlways,
  };
})();
