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

function loadBankQuestions(moduleName) {
  const filePath = path.resolve(`docs/${moduleName}/bank.js`);
  const source = fs.readFileSync(filePath, 'utf8');
  try {
    const sandbox = { window: {} };
    sandbox.globalThis = sandbox.window;
    vm.createContext(sandbox);
    vm.runInContext(source, sandbox);
    const bank = Object.values(sandbox.window).find(Array.isArray);
    if (bank) return bank;
  } catch {}

  const match = source.match(/window\.[A-Z0-9_]+\s*=\s*(\[[\s\S]*\])\s*;?(?:\\n)?\s*$/);
  assert.ok(match, `bank array must parse for ${moduleName}`);
  return JSON.parse(match[1]);
}

function getBankModules() {
  const docsRoot = path.resolve('docs');
  return fs.readdirSync(docsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(docsRoot, entry.name, 'bank.js')))
    .map((entry) => entry.name)
    .sort();
}

const windowObj = loadScripts([
  'docs/shared/report/wrong_detail_data.js',
  'docs/shared/report/practice_from_wrong_engine.js'
]);

test('every current bank kind resolves to non-generic remediation guidance', () => {
  const explain = windowObj.AIMathPracticeFromWrongEngine.explainWrongDetail;
  const generic = explain({}).cause;
  const failures = [];

  getBankModules().forEach((moduleName) => {
    const seen = new Set();
    loadBankQuestions(moduleName).forEach((question) => {
      const key = `${String(question.topic || moduleName)}::${String(question.kind || '')}`;
      if (seen.has(key)) return;
      seen.add(key);
      const detail = explain({
        t: question.topic || moduleName,
        k: question.kind,
        q: question.question,
        ca: question.answer,
      });
      if (detail.cause === generic) failures.push(`${moduleName}/${question.kind}`);
      assert.ok(detail.cause, `${moduleName}/${question.kind}: has cause`);
      assert.ok(detail.concept, `${moduleName}/${question.kind}: has concept`);
      assert.ok(detail.tutor, `${moduleName}/${question.kind}: has tutor`);
    });
  });

  assert.deepEqual(failures, [], `generic remediation fallthroughs: ${failures.join(', ')}`);
});

test('every current bank kind generates usable fallback practice', () => {
  const build = windowObj.AIMathPracticeFromWrongEngine.buildPracticeFromWrong;

  getBankModules().forEach((moduleName) => {
    const seen = new Set();
    loadBankQuestions(moduleName).forEach((question, index) => {
      const key = `${String(question.topic || moduleName)}::${String(question.kind || '')}`;
      if (seen.has(key)) return;
      seen.add(key);
      const practice = build({
        t: question.topic || moduleName,
        k: question.kind,
        q: question.question,
        ca: question.answer,
      }, { mode: 'single', sequence: index });
      assert.ok(practice.q, `${moduleName}/${question.kind}: has question text`);
      assert.ok(practice.hint, `${moduleName}/${question.kind}: has hint`);
      assert.ok(practice.answer !== undefined && practice.answer !== null, `${moduleName}/${question.kind}: has answer`);
      assert.notEqual(String(practice.answer).trim(), '', `${moduleName}/${question.kind}: answer must not be empty`);
      assert.notEqual(String(practice.answer), 'NaN', `${moduleName}/${question.kind}: answer must not be NaN`);
    });
  });
});
