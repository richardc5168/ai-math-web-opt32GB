/**
 * Regression tests for parent-report shared-engine integration.
 * Verifies that weakness_engine ranking, enrichReportData, and
 * cross-engine data flow work correctly end-to-end.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const shared = (relPath) => join(__dirname, '..', 'docs', 'shared', ...relPath.split('/'));

function loadEngine(ctx, ...paths) {
  for (const p of paths) {
    const code = readFileSync(shared(p), 'utf-8');
    vm.runInContext(code, ctx);
  }
}

function makeContext() {
  const ctx = vm.createContext({ window: {}, console });
  loadEngine(ctx,
    'report/weakness_engine.js',
    'report/recommendation_engine.js',
    'report/report_data_builder.js',
    'report/practice_from_wrong_engine.js',
    'report/parent_copy_engine.js'
  );
  return ctx;
}

test('weakness ranking preserves order by score descending', () => {
  const ctx = makeContext();
  const ranked = vm.runInContext(`
    window.AIMathWeaknessEngine.rankWeaknessRows([
      { t: '分數', k: '加法', w: 1, n: 10, h2: 0, h3: 0 },
      { t: '面積', k: '長方形', w: 5, n: 20, h2: 3, h3: 2 },
      { t: '小數', k: '乘法', w: 3, n: 15, h2: 1, h3: 0 }
    ], 3);
  `, ctx);
  assert.equal(ranked.length, 3);
  assert.equal(ranked[0].t, '面積', 'highest-score weakness first');
  assert.equal(ranked[1].t, '小數');
  assert.equal(ranked[2].t, '分數');
  // Each item must have reason and next_action
  for (const row of ranked) {
    assert.ok(row.reason.length > 0, 'reason must be non-empty');
    assert.ok(row.next_action.length > 0, 'next_action must be non-empty');
  }
});

test('enrichReportData adds weeklyFocus and recommendations', () => {
  const ctx = makeContext();
  const result = vm.runInContext(`
    var report = {
      d: {
        h24: { total: 5, correct: 4, accuracy: 80, avgMs: 30000, modules: [] },
        total: 20, correct: 15, accuracy: 75, avgMs: 25000,
        mods: [], wrong: [
          { t: '分數', k: '加法', q: '1/2+1/3=?', sa: '2/5', ca: '5/6', ts: Date.now() }
        ],
        weak: [
          { t: '分數', k: '加法', w: 3, n: 10, h2: 1, h3: 0 }
        ],
        hintDist: [5, 8, 4, 3]
      }
    };
    var enriched = window.AIMathReportDataBuilder.enrichReportData(report);
    JSON.parse(JSON.stringify(enriched));
  `, ctx);
  assert.ok(result.d, 'enriched should have .d');
  assert.ok(result.d.weeklyFocus, 'enriched.d should have weeklyFocus');
  assert.ok(Array.isArray(result.d.weeklyFocus.items), 'weeklyFocus.items should be array');
  assert.ok(result.d.weeklyFocus.items.length <= 4, 'weeklyFocus items max 4');
  assert.ok(Array.isArray(result.d.recommendations), 'enriched.d should have recommendations');
  assert.ok(result.d.recommendations.length <= 3, 'recommendations max 3');
});

test('parent copy engine uses enriched recommendations when available', () => {
  const ctx = makeContext();
  const copy = vm.runInContext(`
    var recs = window.AIMathRecommendationEngine.buildRecommendations({
      report: { total: 20, correct: 15, accuracy: 75, wrong: [], weak: [{ t: '分數', k: '加法', w: 3 }] },
      weak: [{ t: '分數', k: '加法', w: 3 }],
      stuckLevel: 2
    });
    window.AIMathParentCopyEngine.buildParentCopy({
      report: { total: 20, correct: 15, accuracy: 75, weak: [{ t: '分數', k: '加法', w: 3 }], recommendations: recs },
      studentName: '小明',
      days: 7,
      recommendations: recs
    });
  `, ctx);
  assert.ok(copy.includes('小明'), 'copy should include student name');
  assert.ok(copy.includes('75%'), 'copy should include accuracy');
  assert.ok(copy.includes('分數'), 'copy should reference weakness topic');
  assert.ok(copy.includes('接下來先做'), 'copy should include action preamble');
});

test('weakness engine handles empty and edge-case rows', () => {
  const ctx = makeContext();
  const result = vm.runInContext(`
    JSON.parse(JSON.stringify({
      empty: window.AIMathWeaknessEngine.rankWeaknessRows([], 5),
      null_input: window.AIMathWeaknessEngine.rankWeaknessRows(null, 5),
      zero_wrong: window.AIMathWeaknessEngine.rankWeaknessRows([{ t: 'x', k: 'y', w: 0, n: 5, h2: 0, h3: 0 }], 5),
      null_row_reason: window.AIMathWeaknessEngine.describeWeaknessReason(null),
      null_row_action: window.AIMathWeaknessEngine.nextActionText(null)
    }));
  `, ctx);
  assert.equal(result.empty.length, 0, 'empty input should give empty output');
  assert.equal(result.null_input.length, 0, 'null input should give empty output');
  assert.equal(result.zero_wrong.length, 0, 'rows with 0 wrong should be filtered');
  assert.ok(result.null_row_reason.length > 0, 'null row should get fallback reason');
  assert.ok(result.null_row_action.length > 0, 'null row should get fallback action');
});
