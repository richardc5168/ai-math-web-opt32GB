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
  'docs/shared/report/topic_link_map.js',
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
    ['interactive-g56-core-foundation', '../interactive-g56-core-foundation/'],
    ['commercial-pack1-fraction-sprint', '../commercial-pack1-fraction-sprint/'],
    ['interactive-g5-national-bank', '../interactive-g5-national-bank/'],
    ['interactive-g5-midterm1', '../interactive-g5-midterm1/'],
    ['g5-grand-slam', '../g5-grand-slam/']
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

test('remedial cards get reason and action text from weakness engine', () => {
  const weakEngine = windowObj.AIMathWeaknessEngine;

  const rows = [
    { t: 'fraction-word-g5', k: 'addition', w: 5, h2: 2, h3: 1, n: 10 },
    { t: 'volume-g5', k: 'rect_cm3', w: 1, h2: 3, h3: 0, n: 8 }
  ];

  rows.forEach((row) => {
    const reason = weakEngine.describeWeaknessReason(row);
    const action = weakEngine.nextActionText(row);
    assert.ok(reason.length > 5, `reason for ${row.t} should be a meaningful string`);
    assert.ok(action.length > 5, `action for ${row.t} should be a meaningful string`);
    assert.ok(!reason.includes('undefined'), `reason should not contain "undefined"`);
    assert.ok(!action.includes('undefined'), `action should not contain "undefined"`);
  });

  // High wrong count → specific reason
  const highWrong = weakEngine.describeWeaknessReason({ w: 5, h2: 0, h3: 0, n: 10 });
  assert.ok(highWrong.includes('答錯'), `high wrong count should mention 答錯`);

  // High h3 → specific reason
  const highH3 = weakEngine.describeWeaknessReason({ w: 1, h2: 0, h3: 2, n: 5 });
  assert.ok(highH3.includes('提示'), `high h3 should mention 提示`);
});

test('wrong list items include deep-link to practice module', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // The wrong list template should include a deep-link using getTopicLink
  assert.ok(src.includes('getTopicLink(w.t)'), 'wrong list should use getTopicLink for deep-link');
  assert.ok(src.includes('去練習模組'), 'wrong list should have "go to practice module" link text');
});

test('detailed analysis cards include deep-link to practice module', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  // The analysis section should also link to the practice module
  assert.ok(src.includes('前往練習模組'), 'analysis cards should have "go to practice module" link text');
  // Verify the analysis template uses getTopicLink
  const analysisBlock = src.slice(src.indexOf('補強方案'));
  assert.ok(analysisBlock.includes('getTopicLink(w.t)'), 'analysis card should use getTopicLink for deep-link');
});
