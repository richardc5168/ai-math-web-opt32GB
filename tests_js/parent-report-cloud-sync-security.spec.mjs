import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('student auth cloud write tokens are session-scoped and not bundle-config driven', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/student_auth.js'), 'utf8');
  assert.ok(src.includes("sessionStorage.getItem(CLOUD_TOKEN_KEY)"), 'cloud token should be read from sessionStorage');
  assert.ok(src.includes("localStorage.getItem(LEGACY_CLOUD_TOKEN_KEY)"), 'legacy localStorage token should only be read for migration');
  assert.ok(src.includes("localStorage.removeItem(LEGACY_CLOUD_TOKEN_KEY)"), 'legacy localStorage token should be cleared during migration');
  assert.ok(src.includes('setCloudWriteToken'), 'public API should expose a session-scoped runtime token setter');
  assert.ok(src.includes('clearCloudWriteToken'), 'public API should expose a runtime token clear helper');
  assert.ok(!src.includes('AIMathCloudSyncConfig.gistToken'), 'bundle/global gist token injection should be removed');
  assert.ok(!src.includes("localStorage.getItem('aimath_cloud_sync_pat_v1')"), 'persistent localStorage token lookup should be removed');
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
  assert.ok(reportPageSrc.includes('lookupStudentReport(_unlockName, _unlockPin)'), 'refresh should pass the unlocked PIN into the backend lookup');
  assert.ok(reportPageSrc.includes('lookupStudentReport(name, pin)'), 'unlock should rely on backend PIN validation');
});
