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

test('report summary keeps recent wrong answers newest-first', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, student_answer_raw: '2', correct_answer: '3', question_text: 'Q1' },
      { ts: Date.parse('2026-03-16T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, student_answer_raw: '1', correct_answer: '4', question_text: 'Q2' },
      { ts: Date.parse('2026-03-14T08:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: true, student_answer_raw: '24', correct_answer: '24', question_text: 'Q3' }
    ],
    practiceEvents: []
  });

  assert.equal(report.d.wrong[0].q, 'Q2');
  assert.equal(report.d.wrong[1].q, 'Q1');
});

test('weekly focus keeps 4 key KPIs', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false },
      { ts: Date.parse('2026-03-16T08:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: true, max_hint: 2 }
    ],
    practiceEvents: []
  });

  assert.equal(report.d.weeklyFocus.items.length, 4);
});
