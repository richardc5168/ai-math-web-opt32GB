import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';

function loadScripts(files) {
  const sandbox = { window: {}, console, Date, Math, JSON };
  sandbox.globalThis = sandbox.window;
  vm.createContext(sandbox);
  files.forEach((file) => {
    const code = fs.readFileSync(path.resolve(file), 'utf8');
    vm.runInContext(code, sandbox);
  });
  return sandbox.window;
}

const windowObj = loadScripts([
  'docs/shared/report/weakness_engine.js',
  'docs/shared/report/recommendation_engine.js',
  'docs/shared/report/report_data_builder.js'
]);

test('recommendations are capped at top 3 and all links exist', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, max_hint: 3 },
      { ts: Date.parse('2026-03-15T09:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T10:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T11:00:00Z'), unit_id: 'interactive-decimal-g5', kind: 'decimal_mul', ok: false, max_hint: 1 }
    ],
    practiceEvents: []
  });

  assert.equal(report.d.recommendations.length, 3);
  report.d.recommendations.forEach((action) => {
    assert.ok(action.deep_link && action.deep_link.startsWith('../'));
    assert.ok(action.reason.length > 0);
  });
});
