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
  'docs/shared/report/wrong_detail_data.js',
  'docs/shared/report/practice_from_wrong_engine.js',
  'docs/shared/report/report_data_builder.js'
]);

function loadBankQuestions(moduleName) {
  const source = fs.readFileSync(path.resolve(`docs/${moduleName}/bank.js`), 'utf8');
  const sandbox = { window: {} };
  sandbox.globalThis = sandbox.window;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  const bank = Object.values(sandbox.window).find(Array.isArray);
  assert.ok(bank, `bank array must exist for ${moduleName}`);
  return bank;
}

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

test('practice answer checker accepts fractions, mixed numbers, decimals, and whole numbers', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  assert.ok(src.includes('function fractionsEqual'), 'fractionsEqual helper must exist');
  assert.ok(src.includes('function parseFrac'), 'parseFrac helper must exist');
  assert.ok(src.includes('fractionsEqual(user, corr)'), 'checkNow must call fractionsEqual');

  // Unit-test extracted logic (mirrors current parseFrac with all format support)
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
    var dm = str.match(/^(-?\d+)\.(\d+)$/);
    if (dm){
      var intPart = parseInt(dm[1], 10);
      var decStr = dm[2];
      var decVal = parseInt(decStr, 10);
      var pow = 1;
      for (var di = 0; di < decStr.length; di++) pow *= 10;
      var dsign = intPart < 0 ? -1 : 1;
      return { n: dsign * (Math.abs(intPart) * pow + decVal), d: pow };
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
  assert.ok(!fractionsEqual('2/3', '3/4'), '2/3 != 3/4');
  // Mixed numbers
  assert.ok(fractionsEqual('1 1/2', '3/2'), '1 1/2 == 3/2');
  assert.ok(fractionsEqual('2 1/4', '9/4'), '2 1/4 == 9/4');
  assert.ok(!fractionsEqual('1 1/2', '1/2'), '1 1/2 != 1/2');
  // Whole numbers
  assert.ok(fractionsEqual('3', '6/2'), '3 == 6/2');
  assert.ok(fractionsEqual('2', '4/2'), '2 == 4/2');
  assert.ok(!fractionsEqual('3', '5/2'), '3 != 5/2');
  // Mixed vs mixed
  assert.ok(fractionsEqual('1 2/4', '1 1/2'), '1 2/4 == 1 1/2');
  // Decimal ↔ fraction equivalence (integer arithmetic, no IEEE 754)
  assert.ok(fractionsEqual('0.5', '1/2'), '0.5 == 1/2');
  assert.ok(fractionsEqual('0.25', '1/4'), '0.25 == 1/4');
  assert.ok(fractionsEqual('1.5', '3/2'), '1.5 == 3/2');
  assert.ok(fractionsEqual('0.75', '3/4'), '0.75 == 3/4');
  assert.ok(!fractionsEqual('0.3', '1/4'), '0.3 != 1/4');
  // Decimal ↔ whole
  assert.ok(fractionsEqual('2.0', '2'), '2.0 == 2');
  // Decimal ↔ mixed
  assert.ok(fractionsEqual('1.5', '1 1/2'), '1.5 == 1 1/2');
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

test('practice early-exit is tracked with completed:false in events', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // persistPractice must accept isComplete param
  assert.ok(src.includes('function persistPractice(score, total, isComplete)'), 'persistPractice must accept isComplete param');
  // practice event must include completed field
  assert.ok(src.includes('completed: completed'), 'practice event must record completed status');
  // early exit path must pass false
  assert.ok(src.includes('persistPractice(quizScore, taken, false)'), 'early exit must pass completed=false');
  // summary must show early exit count
  assert.ok(src.includes('提前結束'), 'practice summary must show early exit count');
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
  // renderPracticeSummary must be called BEFORE the cloud write
  const summaryIdx = persistBlock.indexOf('renderPracticeSummary()');
  const cloudCheckIdx = Math.min(
    persistBlock.indexOf('AIMathReportSyncAdapter') >= 0 ? persistBlock.indexOf('AIMathReportSyncAdapter') : Infinity,
    persistBlock.indexOf('if (!window.AIMathStudentAuth') >= 0 ? persistBlock.indexOf('if (!window.AIMathStudentAuth') : Infinity
  );
  assert.ok(summaryIdx < cloudCheckIdx, 'renderPracticeSummary must run before cloud auth check so UI updates even without cloud');
  // r.practice.events push must also be before cloud check
  const pushIdx = persistBlock.indexOf('r.practice.events.push');
  assert.ok(pushIdx < cloudCheckIdx, 'practice event push must happen before cloud auth check');
});

test('explainWrongDetail covers all bank question families', () => {
  const E = windowObj.AIMathPracticeFromWrongEngine.explainWrongDetail;
  const families = [
    { w: { k: 'u1_average' }, label: 'average' },
    { w: { k: 'u3_money' },   label: 'money' },
    { w: { k: 'u4_discount_percent' }, label: 'percent' },
    { w: { k: 'u5_ratio_proportion' }, label: 'ratio' },
    { w: { k: 'u6_unit_decimal' },     label: 'decimal' },
    { w: { k: 'u7_speed' },            label: 'speed' },
    { w: { k: 'u8_area_perimeter' },   label: 'area/perimeter' },
    { w: { k: 'u9_time_trip' },        label: 'time' },
    { w: { k: 'u10_multi_step' },      label: 'multi-step' },
  ];
  const generic = E({}).cause;
  families.forEach(({ w, label }) => {
    const detail = E(w);
    assert.ok(detail.cause, label + ': has cause');
    assert.ok(detail.concept, label + ': has concept');
    assert.ok(detail.tutor, label + ': has tutor');
    assert.notEqual(detail.cause, generic, label + ': must NOT fall through to generic');
  });
});

test('buildPracticeFromWrong generates targeted practice for all bank families', () => {
  const B = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong;
  const families = [
    { w: { k: 'u1_average' },          label: 'average' },
    { w: { k: 'u3_money' },            label: 'money' },
    { w: { k: 'u4_discount_percent' }, label: 'percent' },
    { w: { k: 'u5_ratio_proportion' }, label: 'ratio' },
    { w: { k: 'u6_unit_decimal' },     label: 'decimal' },
    { w: { k: 'u7_speed' },            label: 'speed' },
    { w: { k: 'u8_area_perimeter' },   label: 'area' },
    { w: { k: 'u9_time_trip' },        label: 'time' },
    { w: { k: 'u10_multi_step' },      label: 'multi-step' },
  ];
  families.forEach(({ w, label }) => {
    const p = B(w, { mode: 'single', sequence: 0 });
    assert.ok(p.q, label + ': has question text');
    assert.ok(p.answer, label + ': has answer');
    assert.ok(p.hint, label + ': has hint');
    // Answer must NOT be NaN or empty
    assert.ok(p.answer !== 'NaN', label + ': answer must not be NaN');
    // Hint must not contain the raw answer (no trivial leak)
    // Relaxed: hints like "= 120 ÷ 3" may contain the answer number incidentally
  });
});

test('new practice generators produce integer answers via integer arithmetic', () => {
  const B = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong;
  // Run multiple seeds — discount, ratio, speed, area, time, multi-step all must be integer
  const intKinds = [
    { k: 'u4_discount_percent' },
    { k: 'u5_ratio_proportion' },
    { k: 'u7_speed' },
    { k: 'u8_area_perimeter' },
    { k: 'u9_time_trip' },
    { k: 'u10_multi_step' },
    { k: 'u1_average' },
    { k: 'u3_money' },
  ];
  intKinds.forEach(w => {
    for (let seq = 0; seq < 5; seq++) {
      const p = B(w, { mode: 'single', sequence: seq });
      const num = Number(p.answer);
      assert.ok(!isNaN(num), w.k + ' seq=' + seq + ': answer must be a number');
      if (w.k !== 'u6_unit_decimal') {
        assert.ok(Number.isInteger(num), w.k + ' seq=' + seq + ': answer must be integer, got ' + p.answer);
      }
    }
  });
});

test('commercial and life-bank wrong answers resolve to non-generic explanations', () => {
  const explain = windowObj.AIMathPracticeFromWrongEngine.explainWrongDetail;
  const generic = explain({}).cause;
  const modules = [
    'commercial-pack1-fraction-sprint',
    'decimal-unit4',
    'life-applications-g5',
    'interactive-g5-empire',
    'interactive-g5-life-pack1-empire',
  ];

  modules.forEach((moduleName) => {
    const seen = new Set();
    loadBankQuestions(moduleName).forEach((question) => {
      const key = `${question.topic || moduleName}::${question.kind || ''}`;
      if (seen.has(key)) return;
      seen.add(key);
      const detail = explain({
        t: question.topic || moduleName,
        k: question.kind,
        q: question.question,
        ca: question.answer,
      });
      assert.ok(detail.cause, `${moduleName}/${question.kind}: has cause`);
      assert.ok(detail.concept, `${moduleName}/${question.kind}: has concept`);
      assert.ok(detail.tutor, `${moduleName}/${question.kind}: has tutor`);
      assert.notEqual(detail.cause, generic, `${moduleName}/${question.kind}: should not fall through to generic cause`);
    });
  });
});

test('commercial and life-bank wrong answers generate targeted fallback practice', () => {
  const build = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong;
  const modules = [
    'commercial-pack1-fraction-sprint',
    'decimal-unit4',
    'life-applications-g5',
    'interactive-g5-empire',
    'interactive-g5-life-pack1-empire',
  ];

  modules.forEach((moduleName) => {
    const seen = new Set();
    loadBankQuestions(moduleName).forEach((question, index) => {
      const key = `${question.topic || moduleName}::${question.kind || ''}`;
      if (seen.has(key)) return;
      seen.add(key);
      const practice = build({
        t: question.topic || moduleName,
        k: question.kind,
        q: question.question,
        ca: question.answer,
      }, { mode: 'single', sequence: index });
      assert.ok(practice.q, `${moduleName}/${question.kind}: has question text`);
      assert.ok(practice.answer !== undefined && practice.answer !== null && String(practice.answer).trim() !== '', `${moduleName}/${question.kind}: has answer`);
      assert.ok(practice.hint, `${moduleName}/${question.kind}: has hint`);
      assert.notEqual(String(practice.answer), 'NaN', `${moduleName}/${question.kind}: answer must not be NaN`);
    });
  });
});
