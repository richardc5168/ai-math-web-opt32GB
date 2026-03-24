/**
 * attemptTelemetry.test.mjs
 * Regression guard for shared hint trace -> attempt telemetry wiring.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';

function createSandbox() {
  const storage = {
    _data: {},
    getItem(k) { return this._data[k] !== undefined ? this._data[k] : null; },
    setItem(k, v) { this._data[k] = String(v); },
    removeItem(k) { delete this._data[k]; },
  };

  const sandbox = {
    window: {},
    document: {
      getElementById: () => null,
      querySelectorAll: () => [],
      createElement: (tag) => ({
        tagName: tag,
        className: '',
        style: { cssText: '' },
        textContent: '',
        dataset: {},
        id: '',
        appendChild: () => {},
        insertBefore: () => {},
        querySelector: () => null,
        firstChild: null,
      }),
      head: { appendChild: () => {} },
    },
    localStorage: storage,
    sessionStorage: storage,
    setTimeout: (fn) => fn(),
    MutationObserver: class { observe() {} disconnect() {} },
    URLSearchParams,
    console,
    Date,
    Math,
    JSON,
    Object,
    Array,
    String,
    Number,
    RegExp,
  };
  sandbox.window.location = { search: '' };
  sandbox.window.localStorage = storage;
  sandbox.window.sessionStorage = storage;
  sandbox.globalThis = sandbox.window;
  vm.createContext(sandbox);
  return sandbox;
}

function loadScripts(files) {
  const sandbox = createSandbox();
  files.forEach((file) => {
    const code = fs.readFileSync(path.resolve(file), 'utf8');
    vm.runInContext(code, sandbox);
  });
  return sandbox.window;
}

test('attempt telemetry auto-attaches shared hint sequence and timestamps', () => {
  const win = loadScripts([
    'docs/shared/hint_engine.js',
    'docs/shared/attempt_telemetry.js',
  ]);

  win.AIMathHintEngine.setCurrentQuestion({ id: 'q1', question: '1/2 + 1/3 = ?' });
  win.AIMathHintEngine.recordHintOpen(1, { ts: 1111 });
  win.AIMathHintEngine.recordHintOpen(2, { ts: 2222 });

  win.AIMathAttemptTelemetry.appendAttempt('student-1', {
    unit_id: 'fraction-g5',
    kind: 'add_unlike',
    question_id: 'q1',
    ts_start: 1000,
    ts_end: 3000,
    is_correct: false,
    attempts_count: 1,
    hint: { shown_levels: [1, 2], shown_count: 2, total_hint_ms: 0 },
    extra: { source: 'test' },
  }, { maxAttempts: 10 });

  const attempts = win.AIMathAttemptTelemetry.listAttempts('student-1');
  assert.equal(attempts.length, 1);
  assert.deepEqual(attempts[0].hint.hint_sequence, [1, 2]);
  assert.deepEqual(attempts[0].hint.hint_open_ts, [1111, 2222]);
  assert.equal(attempts[0].hint.hint_level_used, 2);
  assert.deepEqual(attempts[0].extra.hint_sequence, [1, 2]);
  assert.deepEqual(attempts[0].extra.hint_open_ts, [1111, 2222]);
  assert.equal(attempts[0].extra.hint_level_used, 2);
});

test('setCurrentQuestion resets shared hint trace for the next question', () => {
  const win = loadScripts([
    'docs/shared/hint_engine.js',
    'docs/shared/attempt_telemetry.js',
  ]);

  win.AIMathHintEngine.setCurrentQuestion({ id: 'q1', question: 'old' });
  win.AIMathHintEngine.recordHintOpen(3, { ts: 3000 });
  win.AIMathHintEngine.setCurrentQuestion({ id: 'q2', question: 'new' });

  const trace = win.AIMathHintEngine.getHintTrace();
  assert.deepEqual(Array.from(trace.hint_sequence), []);
  assert.deepEqual(Array.from(trace.hint_open_ts), []);
  assert.equal(trace.hint_level_used, 0);
  assert.equal(trace.question_id, 'q2');
});

test('explicit hint trace on event is preserved over shared fallback', () => {
  const win = loadScripts([
    'docs/shared/hint_engine.js',
    'docs/shared/attempt_telemetry.js',
  ]);

  win.AIMathHintEngine.setCurrentQuestion({ id: 'q1', question: 'old' });
  win.AIMathHintEngine.recordHintOpen(1, { ts: 1111 });

  win.AIMathAttemptTelemetry.appendAttempt('student-2', {
    unit_id: 'fraction-g5',
    kind: 'add_unlike',
    question_id: 'q1',
    ts_start: 1000,
    ts_end: 3000,
    is_correct: true,
    attempts_count: 1,
    hint: {
      shown_levels: [1],
      shown_count: 1,
      total_hint_ms: 0,
      hint_sequence: [4],
      hint_open_ts: [4444],
      hint_level_used: 4,
    },
    extra: {},
  }, { maxAttempts: 10 });

  const attempt = win.AIMathAttemptTelemetry.listAttempts('student-2')[0];
  assert.deepEqual(attempt.hint.hint_sequence, [4]);
  assert.deepEqual(attempt.hint.hint_open_ts, [4444]);
  assert.equal(attempt.hint.hint_level_used, 4);
  assert.deepEqual(attempt.extra.hint_sequence, [4]);
  assert.deepEqual(attempt.extra.hint_open_ts, [4444]);
  assert.equal(attempt.extra.hint_level_used, 4);
});
