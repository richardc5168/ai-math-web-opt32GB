import type { AttemptEvent, AttemptLogFile } from './attempt_event';

const VERSION: AttemptLogFile['version'] = 1;

export function keyForUser(userId: string): string {
  const uid = String(userId || '').trim() || 'guest';
  return `ai_math_attempts_v1::${uid}`;
}

export function loadAttemptLog(userId: string): AttemptLogFile {
  const key = keyForUser(userId);
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return { version: VERSION, user_id: userId, attempts: [] };
    const obj = JSON.parse(raw);
    if (obj && obj.version === VERSION && Array.isArray(obj.attempts)) return obj;
  } catch {
    // ignore
  }
  return { version: VERSION, user_id: userId, attempts: [] };
}

export function appendAttempt(userId: string, evt: AttemptEvent): { ok: boolean; size: number } {
  const log = loadAttemptLog(userId);
  log.user_id = userId;
  log.attempts.push(evt);
  if (log.attempts.length > 5000) log.attempts.splice(0, log.attempts.length - 5000);
  try {
    localStorage.setItem(keyForUser(userId), JSON.stringify(log));
  } catch {
    return { ok: false, size: log.attempts.length };
  }
  return { ok: true, size: log.attempts.length };
}

export function listAttempts(userId: string, opts?: { sinceMs?: number; limit?: number }): AttemptEvent[] {
  const log = loadAttemptLog(userId);
  let items = log.attempts || [];
  if (opts?.sinceMs != null) {
    const since = Number(opts.sinceMs);
    if (Number.isFinite(since)) items = items.filter((x) => Number(x?.ts_end) >= since);
  }
  if (opts?.limit != null) {
    const limit = Math.max(1, Number(opts.limit));
    items = items.slice(-limit);
  }
  return items.slice();
}

export function clearAttempts(userId: string): void {
  try {
    localStorage.removeItem(keyForUser(userId));
  } catch {
    // ignore
  }
}
