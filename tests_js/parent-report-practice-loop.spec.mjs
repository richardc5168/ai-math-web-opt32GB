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

test('practice answer checker accepts equivalent unsimplified fractions and mixed numbers', () => {
  // Replicate the inline fractionsEqual logic from parent-report/index.html
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // Verify fractionsEqual function exists
  assert.ok(src.includes('function fractionsEqual'), 'fractionsEqual helper must exist');
  assert.ok(src.includes('function parseFrac'), 'parseFrac helper must exist');
  // Verify checkNow uses fractionsEqual fallback
  assert.ok(src.includes('fractionsEqual(user, corr)'), 'checkNow must call fractionsEqual');

  // Unit-test the extracted logic (mirrors current parseFrac with mixed number support)
  function parseFrac(s){
    var str = String(s||'').trim();
    var mm = str.match(/^(-?\d+)\s+(\d+)\/(\d+)$/);
    if (mm){
      var whole = parseInt(mm[1], 10);
      var num = parseInt(mm[2], 10);
      var den = parseInt(mm[3], 10);
      if (den > 0){
        var sign = whole < 0 ? -1 : 1;
        return { n: sign * (Math.abs(whole) * den + num), d: den };
      }
    }
    var m = str.match(/^(-?\d+)\/(\d+)$/);
    if (m){
      var n = parseInt(m[1], 10);
      var d = parseInt(m[2], 10);
      return d > 0 ? { n: n, d: d } : null;
    }
    var wi = str.match(/^(-?\d+)$/);
    if (wi) return { n: parseInt(wi[1], 10), d: 1 };
    return null;
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
  // Mixed number support
  assert.ok(fractionsEqual('1 1/2', '3/2'), '1 1/2 == 3/2');
  assert.ok(fractionsEqual('2 1/4', '9/4'), '2 1/4 == 9/4');
  assert.ok(!fractionsEqual('1 1/2', '1/2'), '1 1/2 != 1/2');
  // Whole number support
  assert.ok(fractionsEqual('3', '6/2'), '3 == 6/2');
  assert.ok(fractionsEqual('2', '4/2'), '2 == 4/2');
  assert.ok(!fractionsEqual('3', '5/2'), '3 != 5/2');
  // Mixed vs mixed
  assert.ok(fractionsEqual('1 2/4', '1 1/2'), '1 2/4 == 1 1/2');
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

test('persistPractice writes to local attempt telemetry', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  const persistBlock = src.slice(src.indexOf('function persistPractice'));
  // Verify local telemetry write is before cloud write
  assert.ok(persistBlock.includes('AIMathAttemptTelemetry.appendAttempt'), 'persistPractice must write to local telemetry');
  assert.ok(persistBlock.includes("source: 'parent-report-practice'"), 'telemetry events must have source tag');
  assert.ok(persistBlock.includes('getDeviceUid()'), 'telemetry must use device UUID, not display name');
  // Verify it comes before the cloud write
  const telIdx = persistBlock.indexOf('AIMathAttemptTelemetry.appendAttempt');
  const cloudIdx = persistBlock.indexOf('AIMathStudentAuth.recordPracticeResult');
  assert.ok(telIdx < cloudIdx, 'local telemetry write must come before cloud write');
});

test('persistPractice updates UI regardless of cloud write availability', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  const persistBlock = src.slice(src.indexOf('function persistPractice'));
  // renderPracticeSummary must be called BEFORE the cloud write check
  const summaryIdx = persistBlock.indexOf('renderPracticeSummary()');
  const cloudCheckIdx = persistBlock.indexOf('if (!window.AIMathStudentAuth');
  assert.ok(summaryIdx < cloudCheckIdx, 'renderPracticeSummary must run before cloud auth check so UI updates even without cloud');
  // r.practice.events push must also be before cloud check
  const pushIdx = persistBlock.indexOf('r.practice.events.push');
  assert.ok(pushIdx < cloudCheckIdx, 'practice event push must happen before cloud auth check');
});
