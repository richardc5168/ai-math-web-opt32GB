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
  'docs/shared/report/recommendation_engine.js'
]);

test('getTopicLink resolves known weakness topics to practice modules', () => {
  const engine = windowObj.AIMathRecommendationEngine;
  assert.ok(engine.getTopicLink);

  // Each known topic should resolve to an actual module path, not the fallback
  const cases = [
    ['fraction-word-g5', '../fraction-word-g5/'],
    ['fraction-g5', '../fraction-g5/'],
    ['volume-g5', '../volume-g5/'],
    ['interactive-decimal-g5', '../interactive-decimal-g5/'],
    ['ratio-percent-g5', '../ratio-percent-g5/'],
    ['life-applications-g5', '../life-applications-g5/'],
    ['interactive-g5-empire', '../interactive-g5-empire/'],
    ['interactive-g56-core-foundation', '../interactive-g56-core-foundation/']
  ];

  cases.forEach(([topic, expected]) => {
    const link = engine.getTopicLink(topic);
    assert.equal(link, expected, `getTopicLink("${topic}") should be "${expected}" but got "${link}"`);
  });
});

test('getTopicLink falls back to star-pack for unknown topics', () => {
  const engine = windowObj.AIMathRecommendationEngine;
  assert.equal(engine.getTopicLink('completely-unknown-topic'), '../star-pack/');
  assert.equal(engine.getTopicLink(''), '../star-pack/');
  assert.equal(engine.getTopicLink(null), '../star-pack/');
});

test('weakness cards get ranked and each has a resolvable topic link', () => {
  const weakEngine = windowObj.AIMathWeaknessEngine;
  const recEngine = windowObj.AIMathRecommendationEngine;

  const weakRows = [
    { t: 'fraction-word-g5', k: 'addition', w: 5, h2: 2, h3: 1 },
    { t: 'volume-g5', k: 'rect_cm3', w: 2, h2: 1, h3: 0 },
    { t: 'interactive-decimal-g5', k: 'decimal_mul', w: 3, h2: 0, h3: 2 }
  ];

  const ranked = weakEngine.rankWeaknessRows(weakRows, 5);
  assert.ok(ranked.length >= 1);

  ranked.forEach((w) => {
    const link = recEngine.getTopicLink(w.t);
    assert.ok(link.startsWith('../'), `link for "${w.t}" should start with "../" but got "${link}"`);
    assert.notEqual(link, '../star-pack/', `known topic "${w.t}" should not fall back to star-pack`);
  });
});
