/**
 * parent-report-data-modules.spec.mjs
 * Regression guard: verifies shared data modules (topic_link_map, wrong_detail_data)
 * are loaded correctly by engines and produce equivalent output.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';

const __dirname = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'));

function loadScripts(files) {
  const sandbox = { window: {}, console, Date, Math, JSON, Object, Array, String, Number, RegExp };
  sandbox.globalThis = sandbox.window;
  vm.createContext(sandbox);
  files.forEach((file) => {
    const code = fs.readFileSync(path.resolve(file), 'utf8');
    vm.runInContext(code, sandbox);
  });
  return sandbox.window;
}

/* ---- Topic Link Map tests ---- */

test('topic_link_map.js exposes TOPIC_LINK_MAP, DEFAULT_LINK, and getTopicLink', () => {
  const win = loadScripts(['docs/shared/report/topic_link_map.js']);
  const tlm = win.AIMathTopicLinkMap;
  assert.ok(tlm, 'AIMathTopicLinkMap should be on window');
  assert.ok(tlm.TOPIC_LINK_MAP, 'TOPIC_LINK_MAP should exist');
  assert.equal(typeof tlm.getTopicLink, 'function');
  assert.equal(tlm.DEFAULT_LINK, '../star-pack/');
});

test('recommendation_engine delegates to topic_link_map', () => {
  const win = loadScripts([
    'docs/shared/report/topic_link_map.js',
    'docs/shared/report/recommendation_engine.js'
  ]);
  const rec = win.AIMathRecommendationEngine;
  const tlm = win.AIMathTopicLinkMap;

  // Both should return the same results
  assert.equal(rec.getTopicLink('fraction-word'), tlm.getTopicLink('fraction-word'));
  assert.equal(rec.getTopicLink('volume'), tlm.getTopicLink('volume'));
  assert.equal(rec.getTopicLink('unknown-xyz'), tlm.DEFAULT_LINK);
});

test('recommendation_engine TOPIC_LINK_MAP is the shared map', () => {
  const win = loadScripts([
    'docs/shared/report/topic_link_map.js',
    'docs/shared/report/recommendation_engine.js'
  ]);
  const rec = win.AIMathRecommendationEngine;
  const tlm = win.AIMathTopicLinkMap;
  assert.equal(rec.TOPIC_LINK_MAP, tlm.TOPIC_LINK_MAP);
});

test('topic_link_map has at least 17 entries and all values are relative paths', () => {
  const win = loadScripts(['docs/shared/report/topic_link_map.js']);
  const map = win.AIMathTopicLinkMap.TOPIC_LINK_MAP;
  const entries = Object.entries(map);
  assert.ok(entries.length >= 17, `Expected >= 17 entries, got ${entries.length}`);
  entries.forEach(([key, value]) => {
    assert.ok(value.startsWith('../'), `value for "${key}" should start with "../" but got "${value}"`);
    assert.ok(value.endsWith('/'), `value for "${key}" should end with "/" but got "${value}"`);
  });
});

/* ---- Wrong Detail Data tests ---- */

test('wrong_detail_data.js exposes RULES, DEFAULT_DETAIL, and lookup', () => {
  const win = loadScripts(['docs/shared/report/wrong_detail_data.js']);
  const wdd = win.AIMathWrongDetailData;
  assert.ok(wdd, 'AIMathWrongDetailData should be on window');
  assert.ok(Array.isArray(wdd.RULES), 'RULES should be an array');
  assert.ok(wdd.RULES.length >= 39, `Expected >= 39 rules, got ${wdd.RULES.length}`);
  assert.equal(typeof wdd.lookup, 'function');
  assert.ok(wdd.DEFAULT_DETAIL.cause);
  assert.ok(wdd.DEFAULT_DETAIL.concept);
  assert.ok(wdd.DEFAULT_DETAIL.tutor);
});

test('practice_from_wrong_engine delegates explainWrongDetail to wrong_detail_data', () => {
  const win = loadScripts([
    'docs/shared/report/wrong_detail_data.js',
    'docs/shared/report/practice_from_wrong_engine.js'
  ]);
  const engine = win.AIMathPracticeFromWrongEngine;
  const wdd = win.AIMathWrongDetailData;

  // Known kinds should match the data module's lookup
  const testCases = [
    { k: 'generic_fraction_word', t: 'fraction-word-g5' },
    { k: 'reverse_fraction', t: 'fraction-sprint' },
    { k: 'cube_cm3', t: 'volume-g5' },
    { k: 'add_unlike', t: 'fraction-g5' },
    { k: 'u1_average', t: 'life-g5' },
    { k: 'temperature_change', t: 'life-g5' },
    { k: 'solve_ax', t: 'core' }
  ];

  testCases.forEach(({ k, t }) => {
    const fromEngine = engine.explainWrongDetail({ k, t });
    const fromData = wdd.lookup(k, t.toLowerCase(), '');
    assert.deepEqual(fromEngine, fromData, `explainWrongDetail({k:"${k}"}) should match data lookup`);
  });
});

test('wrong_detail_data lookup returns DEFAULT_DETAIL for unknown kind', () => {
  const win = loadScripts(['docs/shared/report/wrong_detail_data.js']);
  const wdd = win.AIMathWrongDetailData;
  const result = wdd.lookup('totally_unknown_kind_xyz', 'unknown_mod', '');
  assert.deepEqual(result, wdd.DEFAULT_DETAIL);
});

test('wrong_detail_data lookup matches errType careless fallback', () => {
  const win = loadScripts(['docs/shared/report/wrong_detail_data.js']);
  const wdd = win.AIMathWrongDetailData;
  const result = wdd.lookup('some_unknown_kind', 'unknown_mod', 'careless mistake');
  assert.ok(result.cause.includes('粗心') || result.cause.includes('計算或抄寫'), 'should match careless rule');
  assert.notDeepEqual(result, wdd.DEFAULT_DETAIL);
});

test('no topic_link_map.js means recommendation engine still works (graceful fallback)', () => {
  // Without topic_link_map loaded, recommendation engine should still function
  const win = loadScripts([
    'docs/shared/report/recommendation_engine.js'
  ]);
  const rec = win.AIMathRecommendationEngine;
  // getTopicLink should fall back to star-pack for everything
  assert.equal(rec.getTopicLink('fraction'), '../star-pack/');
  // buildRecommendations should still work
  const recs = rec.buildRecommendations({ report: { accuracy: 50, stuckLevel: 3 }, weak: [{ t: 'fraction', k: 'add' }] });
  assert.ok(recs.length >= 1);
});

test('no wrong_detail_data.js means practice engine still works (graceful fallback)', () => {
  const win = loadScripts([
    'docs/shared/report/practice_from_wrong_engine.js'
  ]);
  const engine = win.AIMathPracticeFromWrongEngine;
  const detail = engine.explainWrongDetail({ k: 'cube_cm3', t: 'volume' });
  // Should return default fallback since data module not loaded
  assert.ok(detail.cause);
  assert.ok(detail.concept);
  assert.ok(detail.tutor);
});

/* ---- Source-level guard: engines must NOT contain inline data ---- */

test('recommendation_engine.js no longer contains inline TOPIC_LINK_MAP entries', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/report/recommendation_engine.js'), 'utf8');
  assert.ok(!src.includes("'commercial-pack1-fraction-sprint'"), 'recommendation_engine should not have inline TOPIC_LINK_MAP entries');
  assert.ok(!src.includes("'../fraction-word-g5/'"), 'recommendation_engine should delegate to topic_link_map');
  assert.ok(src.includes('AIMathTopicLinkMap'), 'recommendation_engine should reference shared topic_link_map');
});

test('practice_from_wrong_engine.js no longer contains inline explainWrongDetail rules', () => {
  const src = fs.readFileSync(path.resolve('docs/shared/report/practice_from_wrong_engine.js'), 'utf8');
  assert.ok(!src.includes('分量應用題容易把對象搞混'), 'practice_from_wrong_engine should not have inline detail text');
  assert.ok(!src.includes('反向分數題容易把乘除方向顛倒'), 'practice_from_wrong_engine should not have inline detail text');
  assert.ok(src.includes('AIMathWrongDetailData'), 'practice_from_wrong_engine should reference shared wrong_detail_data');
});
