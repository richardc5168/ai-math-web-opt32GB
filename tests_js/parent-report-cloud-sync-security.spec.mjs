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
