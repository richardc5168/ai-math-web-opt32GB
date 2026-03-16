import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadEngine() {
  const code = readFileSync(
    path.resolve(__dirname, '..', 'docs', 'shared', 'report', 'practice_summary_engine.js'),
    'utf-8'
  );
  const ctx = { window: {}, Date };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  return ctx.window.AIMathPracticeSummaryEngine;
}

describe('AIMathPracticeSummaryEngine', () => {
  const engine = loadEngine();
  const now = new Date('2025-07-15T12:00:00Z').getTime();

  it('recentEvents filters to 7-day window', () => {
    const events = [
      { ts: now - 2 * 86400000, total: 5, score: 3 },   // 2 days ago — in window
      { ts: now - 10 * 86400000, total: 5, score: 5 },   // 10 days ago — out
      { ts: now - 6 * 86400000, total: 3, score: 2 },    // 6 days ago — in window
    ];
    const recent = engine.recentEvents(events, 7, now);
    assert.equal(recent.length, 2);
  });

  it('recentEvents handles empty and null arrays', () => {
    assert.equal(engine.recentEvents([], 7, now).length, 0);
    assert.equal(engine.recentEvents(null, 7, now).length, 0);
    assert.equal(engine.recentEvents(undefined, 7, now).length, 0);
  });

  it('aggregateStats computes accuracy correctly', () => {
    const events = [
      { ts: now, total: 10, score: 8, topic: '分數', kind: '練習' },
      { ts: now, total: 5, score: 3, topic: '小數', kind: '測驗' },
    ];
    const stats = engine.aggregateStats(events);
    assert.equal(stats.totalQ, 15);
    assert.equal(stats.correctQ, 11);
    assert.equal(stats.acc, 73);  // Math.round(11/15*100)
    assert.equal(stats.count, 2);
  });

  it('aggregateStats returns zeros for empty input', () => {
    const stats = engine.aggregateStats([]);
    assert.equal(stats.totalQ, 0);
    assert.equal(stats.correctQ, 0);
    assert.equal(stats.acc, 0);
    assert.equal(stats.count, 0);
    assert.equal(stats.latestText, '');
  });

  it('groupByKind groups and sorts by total desc', () => {
    const events = [
      { kind: '分數加法', total: 10, score: 8 },
      { kind: '小數乘法', total: 5, score: 3 },
      { kind: '分數加法', total: 10, score: 9 },
    ];
    const rows = engine.groupByKind(events);
    assert.equal(rows.length, 2);
    // 分數加法 has total 20, should be first
    assert.equal(rows[0].k, '分數加法');
    assert.equal(rows[0].total, 20);
    assert.equal(rows[0].score, 17);
    assert.equal(rows[0].acc, 85);  // Math.round(17/20*100)
    assert.equal(rows[0].n, 2);
    // 小數乘法 has total 5
    assert.equal(rows[1].k, '小數乘法');
    assert.equal(rows[1].total, 5);
  });

  it('groupByKind falls back to 未分類 for missing kind/topic', () => {
    const events = [
      { total: 5, score: 3 },
      { kind: '', total: 3, score: 2 },
    ];
    const rows = engine.groupByKind(events);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].k, '未分類');
    assert.equal(rows[0].total, 8);
  });
});
