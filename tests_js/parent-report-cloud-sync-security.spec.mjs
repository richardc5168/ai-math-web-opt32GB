import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('student auth cloud-token internal functions are fully removed', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');
  /* All cloud-token internal functions and their storage keys must be gone */
  assert.ok(!src.includes('CLOUD_TOKEN_KEY'), 'CLOUD_TOKEN_KEY constant must be removed');
  assert.ok(!src.includes('LEGACY_CLOUD_TOKEN_KEY'), 'LEGACY_CLOUD_TOKEN_KEY constant must be removed');
  assert.ok(!src.includes('function getCloudToken'), 'getCloudToken function must be removed');
  assert.ok(!src.includes('function setCloudWriteToken'), 'setCloudWriteToken function must be removed');
  assert.ok(!src.includes('function clearCloudWriteToken'), 'clearCloudWriteToken function must be removed');
  assert.ok(!src.includes('function hasCloudWriteToken'), 'hasCloudWriteToken function must be removed');
  assert.ok(!src.includes('function buildCloudHeaders'), 'buildCloudHeaders function must be removed');
  assert.ok(!src.includes('AIMathCloudSyncConfig.gistToken'), 'bundle/global gist token injection should be removed');
});

test('student auth supports backend base auto-detection and parent report surfaces backend status', () => {
  const authSrc = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  assert.ok(authSrc.includes('function detectParentReportApiBase()'), 'student auth should expose backend base auto-detection');
  assert.ok(authSrc.includes('backend-config.json'), 'student auth should probe backend-config.json as a runtime config hook');
  assert.ok(authSrc.includes('window.location.origin'), 'student auth should support same-origin backend fallback');
  assert.ok(authSrc.includes('aimath:backend-base-ready'), 'student auth should notify pages when backend base becomes available');
  assert.ok(reportSrc.includes('id="backendMsg"'), 'parent report page should show backend availability status');
  assert.ok(reportSrc.includes('detectParentReportApiBase'), 'parent report page should trigger backend base detection');
});


test('parent report cloud sync uses backend registry endpoints on the main write path', () => {
  const authSrc = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');
  const doCloudSyncBlock = authSrc.slice(
    authSrc.indexOf('function doCloudSync()'),
    authSrc.indexOf('function lookupStudentReport')
  );
  const recordPracticeBlock = authSrc.slice(
    authSrc.indexOf('function recordPracticeResult'),
    authSrc.indexOf('/* hook into AIMathAttemptTelemetry.appendAttempt to auto-sync */')
  );
  const reportPageSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  assert.ok(authSrc.includes('function getParentReportApiBase()'), 'student auth should expose a backend base resolver for parent-report sync');
  assert.ok(doCloudSyncBlock.includes('/v1/parent-report/registry/upsert'), 'report sync should write through the backend registry endpoint');
  assert.ok(!doCloudSyncBlock.includes('fetch(GIST_API'), 'report sync should not patch the public gist directly');
  assert.ok(recordPracticeBlock.includes('/v1/parent-report/registry/upsert'), 'practice persistence should use the backend registry endpoint');
  assert.ok(!recordPracticeBlock.includes('fetch(GIST_API'), 'practice persistence should not patch the public gist directly');
  assert.ok(reportPageSrc.includes('readReportSnapshot') || reportPageSrc.includes('lookupStudentReport(_unlockName, _unlockPin)'), 'refresh should use sync adapter or pass the unlocked PIN into the backend lookup');
  assert.ok(reportPageSrc.includes('readReportSnapshot') || reportPageSrc.includes('lookupStudentReport(name, pin)'), 'unlock should rely on sync adapter or backend PIN validation');
  assert.ok(reportPageSrc.includes('report_sync_adapter.js'), 'parent report page should load the report sync adapter');
});

test('report sync adapter credentials are session-scoped and support paid path', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/report_sync_adapter.js'), 'utf8');

  /* Credential storage must use sessionStorage, never localStorage */
  assert.ok(src.includes('sessionStorage.setItem(CRED_KEY'), 'credentials should be stored in sessionStorage');
  assert.ok(src.includes('sessionStorage.getItem(CRED_KEY'), 'credentials should be read from sessionStorage');
  assert.ok(src.includes('sessionStorage.removeItem(CRED_KEY'), 'clearCredentials should remove from sessionStorage');
  assert.ok(!src.includes('localStorage.setItem(CRED_KEY'), 'credentials must never be in localStorage');

  /* Paid path must send X-API-Key header */
  assert.ok(src.includes("'X-API-Key': creds.apiKey"), 'paid write path should attach X-API-Key header');
  assert.ok(src.includes('/v1/app/report_snapshots/latest'), 'paid read path should use subscription-gated endpoint');
  assert.ok(src.includes('/v1/app/report_snapshots'), 'paid write path should use subscription-gated endpoint');

  /* Paid path gate: must check isPaid() before using credentials */
  assert.ok(src.includes('isPaid'), 'adapter must check subscription status before using paid path');

  /* Public API completeness */
  assert.ok(src.includes('setCredentials'), 'adapter must expose setCredentials');
  assert.ok(src.includes('clearCredentials'), 'adapter must expose clearCredentials');
  assert.ok(src.includes('hasCredentials'), 'adapter must expose hasCredentials');

  /* Fall-through: paid path failure should fall back to free path */
  assert.ok(src.includes('_writeSnapshotFree'), 'paid write failure should fall through to free path');
  assert.ok(src.includes('_readSnapshotFree'), 'paid read failure should fall through to free path');
});

test('Gist infrastructure is fully removed from student_auth.js', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');

  /* No Gist constants or URLs */
  assert.ok(!src.includes('GIST_ID'), 'GIST_ID constant must be removed');
  assert.ok(!src.includes('GIST_API'), 'GIST_API constant must be removed');
  assert.ok(!src.includes('api.github.com/gists'), 'Gist API URL must be removed');
  assert.ok(!src.includes('fetch(GIST_API'), 'Gist fetch call must be removed');

  /* No Gist registry parsing helpers (dead code) */
  assert.ok(!src.includes('collectAliasEntries'), 'collectAliasEntries helper must be removed');
  assert.ok(!src.includes('registry.json'), 'registry.json reference must be removed');
  assert.ok(!src.includes('getStoredAttempts'), 'getStoredAttempts helper must be removed');
  assert.ok(!src.includes('getPracticeEventsFromData'), 'getPracticeEventsFromData helper must be removed');

  /* lookupStudentReport must exist and use backend only */
  assert.ok(src.includes('function lookupStudentReport'), 'lookupStudentReport must still exist');
  const lookupBlock = src.slice(
    src.indexOf('function lookupStudentReport('),
    src.indexOf('function recordPracticeResult(')
  );
  assert.ok(lookupBlock.includes('/v1/parent-report/registry/fetch'), 'lookupStudentReport must use backend registry');
  assert.ok(!lookupBlock.includes('github'), 'lookupStudentReport must not reference GitHub');
});

test('no frontend file directly constructs Gist PATCH or write requests', () => {
  const authSrc = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');
  const adapterSrc = fs.readFileSync(path.resolve('docs/shared/report_sync_adapter.js'), 'utf8');
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  /* No file should contain Gist PATCH logic */
  for (const [name, src] of [['student_auth.js', authSrc], ['report_sync_adapter.js', adapterSrc], ['parent-report/index.html', reportSrc]]) {
    assert.ok(!src.includes("method: 'PATCH'"), `${name} must not contain Gist PATCH method`);
    assert.ok(!src.includes('method: "PATCH"'), `${name} must not contain Gist PATCH method (double-quote)`);
  }

  /* The adapter must never reference GIST_API or github.com/gists directly */
  assert.ok(!adapterSrc.includes('api.github.com/gists'), 'adapter must not reference GitHub Gist API directly');
  assert.ok(!adapterSrc.includes('GIST_API'), 'adapter must not reference GIST_API');
  assert.ok(!adapterSrc.includes('GIST_ID'), 'adapter must not reference GIST_ID');

  /* parent-report page must not reference Gist directly */
  assert.ok(!reportSrc.includes('api.github.com/gists'), 'parent report page must not reference GitHub Gist API directly');
});

test('doCloudSync and recordPracticeResult never use direct Gist writes', () => {
  const authSrc = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');

  const doCloudSyncBlock = authSrc.slice(
    authSrc.indexOf('function doCloudSync()'),
    authSrc.indexOf('function lookupStudentReport')
  );
  const recordBlock = authSrc.slice(
    authSrc.indexOf('function recordPracticeResult'),
    authSrc.indexOf('/* hook into AIMathAttemptTelemetry.appendAttempt to auto-sync */')
  );

  /* Both write functions must go through backend registry, never direct Gist */
  assert.ok(!doCloudSyncBlock.includes('fetch(GIST_API'), 'doCloudSync must not fetch Gist directly');
  assert.ok(!doCloudSyncBlock.includes("method: 'PATCH'"), 'doCloudSync must not PATCH Gist');
  assert.ok(!recordBlock.includes('fetch(GIST_API'), 'recordPracticeResult must not fetch Gist directly');
  assert.ok(!recordBlock.includes("method: 'PATCH'"), 'recordPracticeResult must not PATCH Gist');

  /* Both must use backend registry endpoints */
  assert.ok(doCloudSyncBlock.includes('/v1/parent-report/registry/upsert'), 'doCloudSync must use backend registry');
  assert.ok(recordBlock.includes('/v1/parent-report/registry/upsert'), 'recordPracticeResult must use backend registry');
});

test('subscription-gated snapshot endpoints enforce deny-by-default (source-level)', () => {
  const serverSrc = fs.readFileSync(path.resolve('server.py'), 'utf8');

  /* Both snapshot endpoints must require X-API-Key */
  const writeEndpoint = serverSrc.slice(
    serverSrc.indexOf('@app.post("/v1/app/report_snapshots")'),
    serverSrc.indexOf('@app.post("/v1/app/report_snapshots/latest")')
  );
  const readEndpoint = serverSrc.slice(
    serverSrc.indexOf('@app.post("/v1/app/report_snapshots/latest")'),
    serverSrc.indexOf('@app.post("/v1/app/report_snapshots/latest")') + 800
  );

  /* Both must call get_account_by_api_key (auth gate) */
  assert.ok(writeEndpoint.includes('get_account_by_api_key'), 'write endpoint must verify API key');
  assert.ok(readEndpoint.includes('get_account_by_api_key'), 'read endpoint must verify API key');

  /* Both must call ensure_subscription_active (subscription gate) */
  assert.ok(writeEndpoint.includes('ensure_subscription_active'), 'write endpoint must check subscription');
  assert.ok(readEndpoint.includes('ensure_subscription_active'), 'read endpoint must check subscription');

  /* Both must call _verify_student_ownership (ownership gate) */
  assert.ok(writeEndpoint.includes('_verify_student_ownership'), 'write endpoint must verify ownership');
  assert.ok(readEndpoint.includes('_verify_student_ownership'), 'read endpoint must verify ownership');
});

test('cloud-token setter/clearer/checker are NOT exported on the public API surface', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');

  /* Extract the export block: window.AIMathStudentAuth = { ... }; */
  const exportStart = src.indexOf('window.AIMathStudentAuth = {');
  const exportEnd = src.indexOf('};', exportStart);
  assert.ok(exportStart > 0 && exportEnd > exportStart, 'export block must exist');
  const exportBlock = src.slice(exportStart, exportEnd + 2);

  /* These must NOT appear in the export block */
  assert.ok(!exportBlock.includes('setCloudWriteToken'), 'setCloudWriteToken must not be exported');
  assert.ok(!exportBlock.includes('clearCloudWriteToken'), 'clearCloudWriteToken must not be exported');
  assert.ok(!exportBlock.includes('isCloudWriteEnabled'), 'isCloudWriteEnabled must not be exported');
  assert.ok(!exportBlock.includes('hasCloudWriteToken'), 'hasCloudWriteToken must not be exported');
  assert.ok(!exportBlock.includes('getCloudToken'), 'getCloudToken must not be exported');
  assert.ok(!exportBlock.includes('buildCloudHeaders'), 'buildCloudHeaders must not be exported');
});

test('adapter writePracticeEvent has subscription-gated paid path with fallback', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/report_sync_adapter.js'), 'utf8');

  const fnStart = src.indexOf('function writePracticeEvent(');
  const fnEnd = src.indexOf('function _writePracticeEventFree(');
  assert.ok(fnStart > 0 && fnEnd > fnStart, 'writePracticeEvent function must exist');
  const fnBlock = src.slice(fnStart, fnEnd);

  /* Must check paid credentials before routing */
  assert.ok(fnBlock.includes('_isPaidAndCredentialed()'), 'must check paid credentials');
  assert.ok(fnBlock.includes('/v1/app/practice_events'), 'paid path must use subscription-gated endpoint');
  assert.ok(fnBlock.includes("'X-API-Key': creds.apiKey"), 'paid path must send X-API-Key');
  assert.ok(fnBlock.includes('_writePracticeEventFree'), 'must fall through to free path');
});

test('practice_events endpoint enforces deny-by-default (source-level)', () => {
  const serverSrc = fs.readFileSync(path.resolve('server.py'), 'utf8');

  const peStart = serverSrc.indexOf('@app.post("/v1/app/practice_events")');
  assert.ok(peStart > 0, 'practice_events endpoint must exist');
  const peBlock = serverSrc.slice(peStart, peStart + 1200);

  assert.ok(peBlock.includes('get_account_by_api_key'), 'practice_events must verify API key');
  assert.ok(peBlock.includes('ensure_subscription_active'), 'practice_events must check subscription');
  assert.ok(peBlock.includes('_verify_student_ownership'), 'practice_events must verify ownership');
  assert.ok(peBlock.includes('_sanitize_practice_event'), 'practice_events must sanitize event data');
});

test('paid bootstrap uses short-lived token exchange, not raw api_key in URL', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  /* Bootstrap must exist */
  assert.ok(reportSrc.includes('bootstrapPaidSession'), 'parent report must contain paid bootstrap function');

  /* Must use bootstrap token (bt), NOT raw api_key */
  assert.ok(reportSrc.includes("params.get('bt')"), 'bootstrap must read bt (bootstrap token) from URL params');

  /* Must strip bootstrap token from URL immediately */
  assert.ok(reportSrc.includes("searchParams.delete('bt')"), 'bootstrap must strip bt from URL');
  assert.ok(reportSrc.includes('history.replaceState'), 'bootstrap must use replaceState to clean URL');

  /* Must exchange token via POST, not pass raw credentials in URL */
  assert.ok(reportSrc.includes('/v1/app/auth/exchange'), 'bootstrap must use exchange endpoint');
  assert.ok(reportSrc.includes('bootstrap_token'), 'bootstrap must send bootstrap_token in POST body');

  /* Must use adapter.setCredentials (sessionStorage), not direct storage */
  assert.ok(reportSrc.includes('adapter.setCredentials'), 'bootstrap must store credentials through adapter');

  /* Must sync subscription from exchange response */
  assert.ok(reportSrc.includes('syncFromBackend'), 'bootstrap must sync subscription state on success');
});

test('parent-report rejects raw api_key in URL params', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  /* Bootstrap must actively reject raw api_key params */
  const bootstrapBlock = reportSrc.slice(
    reportSrc.indexOf('bootstrapPaidSession'),
    reportSrc.indexOf('if (encodedData)')
  );
  assert.ok(bootstrapBlock.includes("params.get('api_key')"), 'bootstrap must check for raw api_key');
  assert.ok(bootstrapBlock.includes("searchParams.delete('api_key')"), 'bootstrap must strip raw api_key');

  /* The page must NOT use raw api_key for any fetch/whoami call */
  const afterBootstrap = reportSrc.slice(reportSrc.indexOf('if (encodedData)'));
  assert.ok(!afterBootstrap.includes("'X-API-Key': paidKey"), 'page must not use raw api_key for whoami');
});

test('bootstrap/exchange endpoints enforce deny-by-default (source-level)', () => {
  const authSrc = fs.readFileSync(path.resolve('routers/auth.py'), 'utf8');

  /* Bootstrap endpoint must exist and enforce all gates */
  const bsStart = authSrc.indexOf('@auth_router.post("/bootstrap"');
  assert.ok(bsStart > 0, 'bootstrap endpoint must exist');
  const bsBlock = authSrc.slice(bsStart, bsStart + 1800);
  assert.ok(bsBlock.includes('get_account_by_api_key'), 'bootstrap must verify API key');
  assert.ok(bsBlock.includes('ensure_subscription_active'), 'bootstrap must check subscription');
  assert.ok(bsBlock.includes('_verify_student_ownership'), 'bootstrap must verify ownership');
  assert.ok(bsBlock.includes('token_urlsafe'), 'bootstrap must generate secure random token');

  /* Exchange endpoint must exist and consume token */
  const exStart = authSrc.indexOf('@auth_router.post("/exchange"');
  assert.ok(exStart > 0, 'exchange endpoint must exist');
  const exBlock = authSrc.slice(exStart, exStart + 1400);
  assert.ok(exBlock.includes('_consume_bootstrap_token'), 'exchange must consume token via DB — single use');
  assert.ok(exBlock.includes('ensure_subscription_active'), 'exchange must re-validate subscription');
});

test('bootstrap/exchange/login endpoints have rate limiting and token cap (source-level)', () => {
  const serverSrc = fs.readFileSync(path.resolve('server.py'), 'utf8');
  const authSrc = fs.readFileSync(path.resolve('routers/auth.py'), 'utf8');

  /* Rate limiter infrastructure must exist */
  assert.ok(serverSrc.includes('_check_rate_limit'), 'server must have _check_rate_limit function');
  assert.ok(serverSrc.includes('_RATE_LIMIT_BOOTSTRAP'), 'server must define bootstrap rate limit');
  assert.ok(serverSrc.includes('_RATE_LIMIT_EXCHANGE'), 'server must define exchange rate limit');
  assert.ok(serverSrc.includes('_RATE_LIMIT_LOGIN'), 'server must define login rate limit');

  /* Login endpoint must check rate limit before credential validation */
  const loginStart = authSrc.indexOf('@auth_router.post("/login"');
  assert.ok(loginStart > 0, 'login endpoint must exist');
  const loginBlock = authSrc.slice(loginStart, loginStart + 3200);
  assert.ok(loginBlock.includes('_check_rate_limit'), 'login must call rate limiter');
  assert.ok(loginBlock.includes('429'), 'login must return 429 on rate limit');
  /* Rate limit must appear before credential check (username lookup) */
  const rlPos = loginBlock.indexOf('_check_rate_limit');
  const credPos = loginBlock.indexOf('WHERE au.username');
  assert.ok(rlPos < credPos, 'login rate limit must fire BEFORE credential lookup');

  /* Account-level lockout must exist and fire before credential validation */
  assert.ok(serverSrc.includes('_LOGIN_LOCKOUT_THRESHOLD'), 'server must define lockout threshold');
  assert.ok(serverSrc.includes('_LOGIN_LOCKOUT_DURATION_S'), 'server must define lockout duration');
  assert.ok(serverSrc.includes('login_failures'), 'server must have login_failures table');
  assert.ok(loginBlock.includes('_is_account_locked'), 'login must check account lockout');
  assert.ok(loginBlock.includes('423'), 'login must return 423 on lockout');
  const lockoutPos = loginBlock.indexOf('_is_account_locked');
  assert.ok(lockoutPos < credPos, 'account lockout must fire BEFORE credential lookup');

  /* Login failure logging must exist */
  assert.ok(serverSrc.includes('_auth_logger'), 'server must have auth event logger');
  assert.ok(loginBlock.includes('login_failure'), 'login must log failure events');
  assert.ok(loginBlock.includes('login_success'), 'login must log success events');
  assert.ok(loginBlock.includes('login_lockout'), 'login must log lockout events');

  /* Admin login-failures audit endpoint must exist */
  assert.ok(serverSrc.includes('/v1/app/admin/login-failures'), 'admin login-failures endpoint must exist');
  const adminLfStart = serverSrc.indexOf('/v1/app/admin/login-failures');
  const adminLfBlock = serverSrc.slice(adminLfStart, adminLfStart + 2200);
  assert.ok(adminLfBlock.includes('X-Admin-Token'), 'admin login-failures must require admin token');
  /* Admin endpoint must include summary statistics and alert level */
  assert.ok(adminLfBlock.includes('"summary"'), 'admin response must include summary object');
  assert.ok(adminLfBlock.includes('alert_level'), 'admin response must include alert_level');
  assert.ok(adminLfBlock.includes('locked_accounts'), 'admin response must include locked_accounts');
  assert.ok(adminLfBlock.includes('unique_ips'), 'admin response must include unique_ips count');
  assert.ok(adminLfBlock.includes('unique_usernames'), 'admin response must include unique_usernames count');

  /* Bootstrap endpoint must check rate limit and token cap */
  const bsStart = authSrc.indexOf('@auth_router.post("/bootstrap"');
  const bsBlock = authSrc.slice(bsStart, bsStart + 1800);
  assert.ok(bsBlock.includes('_check_rate_limit'), 'bootstrap must call rate limiter');
  assert.ok(bsBlock.includes('429'), 'bootstrap must return 429 on rate limit');
  assert.ok(bsBlock.includes('_MAX_OUTSTANDING_TOKENS_PER_ACCOUNT'), 'bootstrap must enforce per-account token cap');

  /* Exchange endpoint must check rate limit */
  const exStart = authSrc.indexOf('@auth_router.post("/exchange"');
  const exBlock = authSrc.slice(exStart, exStart + 1400);
  assert.ok(exBlock.includes('_check_rate_limit'), 'exchange must call rate limiter');
  assert.ok(exBlock.includes('429'), 'exchange must return 429 on rate limit');
});

test('subscription syncFromBackend is session-scoped (not localStorage)', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/subscription.js'), 'utf8');

  /* syncFromBackend must exist and be exported */
  assert.ok(src.includes('function syncFromBackend'), 'syncFromBackend function must exist');
  const exportStart = src.indexOf('window.AIMathSubscription = {');
  const exportEnd = src.indexOf('};', exportStart);
  const exportBlock = src.slice(exportStart, exportEnd + 2);
  assert.ok(exportBlock.includes('syncFromBackend'), 'syncFromBackend must be exported');
  assert.ok(exportBlock.includes('clearBackendSync'), 'clearBackendSync must be exported');

  /* syncFromBackend must NOT write to localStorage — it uses in-memory _backendPaidStatus */
  const fnStart = src.indexOf('function syncFromBackend');
  const fnEnd = src.indexOf('function clearBackendSync');
  assert.ok(fnStart > 0 && fnEnd > fnStart, 'syncFromBackend and clearBackendSync must exist');
  const fnBlock = src.slice(fnStart, fnEnd);
  assert.ok(!fnBlock.includes('localStorage'), 'syncFromBackend must not use localStorage');
  assert.ok(!fnBlock.includes('save('), 'syncFromBackend must not persist to localStorage via save()');

  /* getEffectiveSub must check _backendPaidStatus */
  const esStart = src.indexOf('function getEffectiveSub');
  const esEnd = src.indexOf('function defaultSourceForContext');
  const esBlock = src.slice(esStart, esEnd);
  assert.ok(esBlock.includes('_backendPaidStatus'), 'getEffectiveSub must check backend paid status');
  assert.ok(esBlock.includes("entitled_via: 'backend'"), 'backend-entitled sub must set entitled_via to backend');
});

test('paid login UI uses 3-step auth flow (login → bootstrap → exchange)', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  /* Paid login section must exist */
  assert.ok(reportSrc.includes('paidLoginSection'), 'paid login UI section must exist');
  assert.ok(reportSrc.includes('btnPaidLogin'), 'paid login button must exist');
  assert.ok(reportSrc.includes('paidUsername'), 'paid username input must exist');
  assert.ok(reportSrc.includes('paidPassword'), 'paid password input must exist');

  /* Must call all 3 endpoints in sequence */
  assert.ok(reportSrc.includes('/v1/app/auth/login'), 'paid login must call login endpoint');
  assert.ok(reportSrc.includes('/v1/app/auth/bootstrap'), 'paid login must call bootstrap endpoint');
  assert.ok(reportSrc.includes('/v1/app/auth/exchange'), 'paid login must call exchange endpoint');

  /* Must use adapter.setCredentials at the end (sessionStorage, not localStorage) */
  assert.ok(reportSrc.includes('adapter.setCredentials(res3.body.api_key, res3.body.student_id)'),
    'paid login must store credentials via adapter at exchange step, not login step');

  /* Must sync subscription from exchange response */
  const loginBlock = reportSrc.slice(reportSrc.indexOf('initPaidLogin'));
  assert.ok(loginBlock.includes('syncFromBackend(res3.body.subscription)'),
    'paid login must sync subscription from exchange response (not login response)');
});

test('paid login never stores raw login api_key durably', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');

  /* Extract the paid login IIFE */
  const loginBlock = reportSrc.slice(
    reportSrc.indexOf('initPaidLogin'),
    reportSrc.indexOf('if (encodedData)')
  );

  /* Raw api_key from login must NOT be stored in localStorage or sessionStorage */
  assert.ok(!loginBlock.includes('localStorage.setItem') || !loginBlock.includes('loginApiKey'),
    'paid login must not store loginApiKey in localStorage');
  assert.ok(!loginBlock.includes("sessionStorage.setItem(") ||
    (loginBlock.includes("sessionStorage.setItem(") && !loginBlock.includes('loginApiKey')),
    'paid login must not store raw loginApiKey in sessionStorage directly');

  /* loginApiKey must be used only in-scope: declare, proceedWithStudent param, bootstrap header, call sites */
  const apiKeyUsages = loginBlock.split('loginApiKey').length - 1;
  assert.ok(apiKeyUsages <= 7, 'loginApiKey should be used minimally (declare + param + header + call sites, found ' + apiKeyUsages + ')');
  /* loginApiKey MUST NOT appear in any storage API */
  assert.ok(!loginBlock.match(/(?:local|session)Storage\.\w+\(.*loginApiKey/), 'loginApiKey must never be stored in browser storage');

  /* Password must be cleared from DOM after success */
  assert.ok(loginBlock.includes("getElementById('paidPassword').value = ''"),
    'paid login must clear password from DOM on success');
});

test('paid login handles error responses without leaking credentials', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  const loginBlock = reportSrc.slice(
    reportSrc.indexOf('initPaidLogin'),
    reportSrc.indexOf('if (encodedData)')
  );

  /* Must handle 401, 402, 403 error codes */
  assert.ok(loginBlock.includes('res.status === 401'), 'must handle 401 (bad credentials)');
  assert.ok(loginBlock.includes('res.status === 402'), 'must handle 402 (subscription expired)');
  assert.ok(loginBlock.includes('res.status === 403'), 'must handle 403 (account disabled)');

  /* Must re-enable button on failure */
  const disableCount = (loginBlock.match(/btnLogin\.disabled = false/g) || []).length;
  assert.ok(disableCount >= 5, 'button must be re-enabled on all error paths (found ' + disableCount + ')');

  /* Must NOT call setCredentials on error paths — only on final success */
  const setCredCalls = (loginBlock.match(/adapter\.setCredentials\(/g) || []).length;
  assert.ok(setCredCalls === 1, 'setCredentials must be called exactly once (on success), found ' + setCredCalls);
});

test('student selector UI for multi-student accounts (source-level)', () => {
  const reportSrc = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  const loginBlock = reportSrc.slice(
    reportSrc.indexOf('initPaidLogin'),
    reportSrc.indexOf('if (encodedData)')
  );

  /* HTML must have student selector elements */
  assert.ok(reportSrc.includes('id="studentSelectorWrap"'), 'must have studentSelectorWrap container');
  assert.ok(reportSrc.includes('id="studentSelector"'), 'must have studentSelector dropdown');
  assert.ok(reportSrc.includes('id="btnSelectStudent"'), 'must have btnSelectStudent button');

  /* Login block must use res.body.students array */
  assert.ok(loginBlock.includes('res.body.students'), 'must read students array from login response');

  /* Single student → auto-proceed without selector */
  assert.ok(loginBlock.includes('students.length <= 1'), 'must auto-proceed for single-student accounts');

  /* Multiple students → show selector */
  assert.ok(loginBlock.includes('selectorWrap.style.display'), 'must toggle selector visibility');
  assert.ok(loginBlock.includes('selectorEl.innerHTML'), 'must populate selector options');
  assert.ok(loginBlock.includes("s.display_name"), 'must show student display_name in selector');

  /* proceedWithStudent must be used for bootstrap+exchange */
  assert.ok(loginBlock.includes('proceedWithStudent('), 'must use proceedWithStudent helper for bootstrap+exchange');

  /* Backend login response must include students array */
  const authSrc = fs.readFileSync(path.resolve('routers/auth.py'), 'utf8');
  const loginFn = authSrc.slice(
    authSrc.indexOf('def app_auth_login'),
    authSrc.indexOf('def app_auth_whoami')
  );
  assert.ok(loginFn.includes('"students":'), 'server login response must include students array');
});
