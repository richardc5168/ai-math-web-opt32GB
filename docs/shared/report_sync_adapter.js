/*
  AIMathReportSyncAdapter
  ────────────────────────
  Single sync surface for parent-report read/write operations.
  The frontend should use ONLY this adapter — never assemble
  Gist URLs or cloud-write paths directly.

  Paid (subscription-gated) path:
    Uses X-API-Key + student_id credentials.
    Write → POST /v1/app/report_snapshots
    Read  → POST /v1/app/report_snapshots/latest

  Free / legacy path:
    Write → POST /v1/parent-report/registry/upsert (name + PIN)
    Read  → POST /v1/parent-report/registry/fetch  (name + PIN)
            fallback: public Gist read-only

  Local-only fallback:
    If neither backend nor Gist is reachable, the frontend
    keeps data in localStorage only. No cloud write attempt.
*/
(function () {
  'use strict';

  var CRED_KEY = 'aimath_report_creds_v1';

  /* ─── helpers ─── */
  function getAuth() {
    return window.AIMathStudentAuth || null;
  }

  function hasBackend() {
    var auth = getAuth();
    return !!(auth && typeof auth.getParentReportApiBase === 'function' && auth.getParentReportApiBase());
  }

  function buildApiUrl(path) {
    var auth = getAuth();
    if (!auth || typeof auth.getParentReportApiBase !== 'function') return '';
    var base = auth.getParentReportApiBase();
    if (!base) return '';
    return base + path;
  }

  function postApi(path, payload, extraHeaders) {
    var url = buildApiUrl(path);
    if (!url) return Promise.resolve({ ok: false, reason: 'no_backend' });
    var headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    if (extraHeaders) {
      Object.keys(extraHeaders).forEach(function (k) { headers[k] = extraHeaders[k]; });
    }
    return fetch(url, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload || {})
    })
      .then(function (resp) {
        return resp.text().then(function (text) {
          var body = null;
          try { body = text ? JSON.parse(text) : null; } catch (e) { /* ignore */ }
          return { ok: resp.ok, status: resp.status, body: body };
        });
      })
      .catch(function (err) {
        return { ok: false, reason: 'network', detail: String(err) };
      });
  }

  /* ─── credential management (subscription-gated) ─── */
  function _loadCreds() {
    try {
      var raw = sessionStorage.getItem(CRED_KEY);
      if (!raw) return null;
      var c = JSON.parse(raw);
      if (c && typeof c.apiKey === 'string' && c.apiKey && typeof c.studentId === 'number' && c.studentId > 0) return c;
    } catch (e) { /* ignore */ }
    return null;
  }

  function _saveCreds(apiKey, studentId) {
    try {
      sessionStorage.setItem(CRED_KEY, JSON.stringify({ apiKey: apiKey, studentId: studentId }));
    } catch (e) { /* ignore */ }
  }

  function _clearCreds() {
    try { sessionStorage.removeItem(CRED_KEY); } catch (e) { /* ignore */ }
  }

  function _isPaidAndCredentialed() {
    if (!hasBackend()) return false;
    var creds = _loadCreds();
    if (!creds) return false;
    var sub = window.AIMathSubscription;
    if (sub && typeof sub.isPaid === 'function') return sub.isPaid();
    return false;
  }

  /* ─── public API ─── */

  /**
   * Check whether cloud write is available.
   * True when backend is configured (either paid or free path).
   */
  function isCloudWriteAvailable() {
    return hasBackend();
  }

  /**
   * Store subscription credentials for the paid write/read path.
   * Credentials are kept in sessionStorage (cleared when tab closes).
   * @param {string} apiKey    - the X-API-Key for the backend
   * @param {number} studentId - the backend student ID
   */
  function setCredentials(apiKey, studentId) {
    var key = String(apiKey || '').trim();
    var id = parseInt(studentId, 10);
    if (!key || !id || id <= 0) return false;
    _saveCreds(key, id);
    return true;
  }

  /** Remove stored subscription credentials. */
  function clearCredentials() {
    _clearCreds();
  }

  /** Check whether subscription credentials are available. */
  function hasCredentials() {
    return !!_loadCreds();
  }

  /**
   * Write a full report snapshot.
   * Paid path: POST /v1/app/report_snapshots (X-API-Key + student_id)
   * Free path: POST /v1/parent-report/registry/upsert (name + PIN)
   * @param {string} name       - student display name
   * @param {string} pin        - parent PIN (4-6 digits)
   * @param {object} reportData - the report payload
   * @returns {Promise<{ok:boolean, cloud_ts?:number, reason?:string}>}
   */
  function writeReportSnapshot(name, pin, reportData) {
    if (!hasBackend()) {
      return Promise.resolve({ ok: false, reason: 'no_backend' });
    }

    /* Paid path */
    if (_isPaidAndCredentialed()) {
      var creds = _loadCreds();
      return postApi('/v1/app/report_snapshots', {
        student_id: creds.studentId,
        report_payload: reportData,
        source: 'frontend'
      }, { 'X-API-Key': creds.apiKey }).then(function (resp) {
        if (resp.ok && resp.body) {
          return { ok: true, cloud_ts: Date.now(), paid: true };
        }
        if (resp.status === 402) {
          return { ok: false, reason: 'subscription_inactive', status: 402 };
        }
        /* Fall through to free path on auth errors */
        return _writeSnapshotFree(name, pin, reportData);
      });
    }

    /* Free path */
    return _writeSnapshotFree(name, pin, reportData);
  }

  function _writeSnapshotFree(name, pin, reportData) {
    var displayName = String(name || '').trim();
    var pinStr = String(pin || '').trim();
    if (!displayName) return Promise.resolve({ ok: false, reason: 'missing_name' });
    if (!/^\d{4,6}$/.test(pinStr)) return Promise.resolve({ ok: false, reason: 'invalid_pin' });

    return postApi('/v1/parent-report/registry/upsert', {
      name: displayName,
      pin: pinStr,
      report_data: reportData
    }).then(function (resp) {
      if (resp.ok && resp.body) {
        return { ok: true, cloud_ts: resp.body.cloud_ts || 0 };
      }
      return {
        ok: false,
        reason: resp.status === 403 ? 'invalid_pin' : (resp.reason || 'backend_error'),
        status: resp.status
      };
    });
  }

  /**
   * Read the latest report snapshot.
   * Paid path: POST /v1/app/report_snapshots/latest (X-API-Key + student_id)
   * Free path: lookupStudentReport (backend → Gist fallback)
   * @param {string} name - student display name
   * @param {string} pin  - parent PIN
   * @returns {Promise<{data?:object, cloud_ts?:number, error?:string}|null>}
   */
  function readReportSnapshot(name, pin) {
    /* Paid path */
    if (_isPaidAndCredentialed()) {
      var creds = _loadCreds();
      return postApi('/v1/app/report_snapshots/latest', {
        student_id: creds.studentId
      }, { 'X-API-Key': creds.apiKey }).then(function (resp) {
        if (resp.ok && resp.body && resp.body.snapshot) {
          var s = resp.body.snapshot;
          return {
            data: s.report_payload,
            cloud_ts: Date.parse(s.updated_at) || Date.now(),
            source: 'paid_backend'
          };
        }
        if (resp.status === 402) {
          /* Subscription inactive — fall through to free path */
          return _readSnapshotFree(name, pin);
        }
        if (resp.status === 404) {
          /* No snapshot yet — fall through to free path */
          return _readSnapshotFree(name, pin);
        }
        return _readSnapshotFree(name, pin);
      }).catch(function () {
        return _readSnapshotFree(name, pin);
      });
    }

    /* Free path */
    return _readSnapshotFree(name, pin);
  }

  function _readSnapshotFree(name, pin) {
    var auth = getAuth();
    if (auth && typeof auth.lookupStudentReport === 'function') {
      return auth.lookupStudentReport(name, pin);
    }
    return Promise.resolve(null);
  }

  /**
   * Write a single practice event through the backend.
   * @param {string} name   - student display name
   * @param {string} pin    - parent PIN
   * @param {object} event  - practice event { ts, score, total, topic, kind, mode, completed }
   * @returns {Promise<boolean>}
   */
  function writePracticeEvent(name, pin, event) {
    if (!hasBackend()) return Promise.resolve(false);

    /* Paid path */
    if (_isPaidAndCredentialed()) {
      var creds = _loadCreds();
      return postApi('/v1/app/practice_events', {
        student_id: creds.studentId,
        event: event
      }, { 'X-API-Key': creds.apiKey }).then(function (resp) {
        if (resp.ok) return true;
        /* Fall through to free path on auth/subscription errors */
        return _writePracticeEventFree(name, pin, event);
      });
    }

    /* Free path */
    return _writePracticeEventFree(name, pin, event);
  }

  function _writePracticeEventFree(name, pin, event) {
    var displayName = String(name || '').trim();
    var pinStr = String(pin || '').trim();
    if (!displayName || !/^\d{4,6}$/.test(pinStr)) return Promise.resolve(false);

    return postApi('/v1/parent-report/registry/upsert', {
      name: displayName,
      pin: pinStr,
      practice_event: event
    }).then(function (resp) {
      return !!(resp && resp.ok);
    });
  }

  /**
   * Configure the backend base URL.
   * @param {string} base - e.g. 'https://myserver.example.com'
   */
  function setBackendBase(base) {
    var auth = getAuth();
    if (auth && typeof auth.setParentReportApiBase === 'function') {
      auth.setParentReportApiBase(base);
    }
  }

  /**
   * Get the current backend base URL.
   * @returns {string}
   */
  function getBackendBase() {
    var auth = getAuth();
    if (auth && typeof auth.getParentReportApiBase === 'function') {
      return auth.getParentReportApiBase();
    }
    return '';
  }

  /* ─── export ─── */
  window.AIMathReportSyncAdapter = {
    isCloudWriteAvailable: isCloudWriteAvailable,
    writeReportSnapshot: writeReportSnapshot,
    readReportSnapshot: readReportSnapshot,
    writePracticeEvent: writePracticeEvent,
    setBackendBase: setBackendBase,
    getBackendBase: getBackendBase,
    setCredentials: setCredentials,
    clearCredentials: clearCredentials,
    hasCredentials: hasCredentials
  };
})();
