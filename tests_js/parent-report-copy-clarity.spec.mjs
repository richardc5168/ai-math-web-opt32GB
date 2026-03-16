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
  'docs/shared/report/parent_copy_engine.js'
]);

test('parent copy stays concise and action-oriented', () => {
  const text = windowObj.AIMathParentCopyEngine.buildParentCopy({
    studentName: 'Kai',
    report: {
      total: 12,
      accuracy: 67,
      weak: [{ t: 'fraction-word-g5' }, { t: 'volume-g5' }],
      wrong: [{ t: 'fraction-word-g5', sa: '2', ca: '3' }],
      practice: { summary: { total_events: 2, total_questions: 4, accuracy: 75 } },
      recommendations: [
        { concept: 'fraction-word-g5', action_text: '先補最常錯的題型。' },
        { concept: '列式與拆題', action_text: '先練題意轉算式。' },
        { concept: '正確率回穩', action_text: '每天做 5 到 10 題基礎題。' }
      ]
    },
    days: 7
  });

  assert.match(text, /接下來先做 3 件事/);
  assert.match(text, /目前最需要補強/);
  assert.ok(text.split('\n').length <= 12);
});
