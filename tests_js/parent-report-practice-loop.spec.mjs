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

test('practice answer checker accepts equivalent unsimplified fractions', () => {
  // Replicate the inline fractionsEqual logic from parent-report/index.html
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // Verify fractionsEqual function exists
  assert.ok(src.includes('function fractionsEqual'), 'fractionsEqual helper must exist');
  assert.ok(src.includes('function parseFrac'), 'parseFrac helper must exist');
  // Verify checkNow uses fractionsEqual fallback
  assert.ok(src.includes('fractionsEqual(user, corr)'), 'checkNow must call fractionsEqual');

  // Unit-test the extracted logic
  function parseFrac(s){
    var m = String(s||'').match(/^(-?\d+)\/(\d+)$/);
    if (!m) return null;
    var n = parseInt(m[1], 10);
    var d = parseInt(m[2], 10);
    return d > 0 ? { n: n, d: d } : null;
  }
  function fractionsEqual(a, b){
    var fa = parseFrac(a);
    var fb = parseFrac(b);
    if (!fa || !fb) return false;
    return fa.n * fb.d === fb.n * fa.d;
  }
  // Equivalent fractions
  assert.ok(fractionsEqual('2/4', '1/2'), '2/4 == 1/2');
  assert.ok(fractionsEqual('3/9', '1/3'), '3/9 == 1/3');
  assert.ok(fractionsEqual('6/8', '3/4'), '6/8 == 3/4');
  // Non-equivalent
  assert.ok(!fractionsEqual('2/3', '3/4'), '2/3 != 3/4');
  // Non-fraction strings
  assert.ok(!fractionsEqual('42', '42'), 'integers are not fractions');
  assert.ok(!fractionsEqual('abc', '1/2'), 'non-numeric not a fraction');
});

test('single-mode practice persists each answered question individually', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // In single mode (non-quiz), goNext should call persistPractice for each answered question
  // Verify the else branch in goNext resets quizRecorded and calls persistPractice
  const goNextBlock = src.slice(src.indexOf('function goNext()'));
  assert.ok(goNextBlock.includes('} else {'), 'goNext must have an else branch for single mode');
  assert.ok(goNextBlock.includes('quizRecorded = false'), 'single mode must reset quizRecorded before persist');
  assert.ok(goNextBlock.includes('persistPractice(isCorrect ? 1 : 0, 1)'), 'single mode must persist with score 0 or 1');
});
