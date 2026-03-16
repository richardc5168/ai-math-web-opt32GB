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
  'docs/shared/report/practice_from_wrong_engine.js',
  'docs/shared/report/report_data_builder.js'
]);

test('practice generation is deterministic for same wrong answer and sequence', () => {
  const wrong = { t: 'fraction-word-g5', k: 'generic_fraction_word', q: '原題', ca: '3' };
  const first = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong(wrong, { mode: 'single', sequence: 0 });
  const second = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong(wrong, { mode: 'single', sequence: 0 });
  assert.deepEqual(first, second);
});

test('practice summary aggregates retry results in 7-day window', () => {
  const practice = windowObj.AIMathReportDataBuilder.buildPracticeSection([
    { ts: Date.parse('2026-03-15T08:00:00Z'), score: 1, total: 1, kind: 'generic_fraction_word', topic: 'fraction-word-g5', mode: 'retry' },
    { ts: Date.parse('2026-03-16T08:00:00Z'), score: 2, total: 3, kind: 'generic_fraction_word', topic: 'fraction-word-g5', mode: 'quiz3' }
  ], Date.parse('2026-03-16T12:00:00Z'));

  assert.equal(practice.summary.total_events, 2);
  assert.equal(practice.summary.total_questions, 4);
  assert.equal(practice.summary.correct_questions, 3);
  assert.equal(practice.summary.accuracy, 75);
});
