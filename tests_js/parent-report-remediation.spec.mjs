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
  'docs/shared/report/recommendation_engine.js',
  'docs/shared/report/report_data_builder.js'
]);

test('recommendations are capped at top 3 and all links exist', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, max_hint: 3 },
      { ts: Date.parse('2026-03-15T09:00:00Z'), unit_id: 'fraction-word-g5', kind: 'generic_fraction_word', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T10:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T11:00:00Z'), unit_id: 'interactive-decimal-g5', kind: 'decimal_mul', ok: false, max_hint: 1 }
    ],
    practiceEvents: []
  });

  assert.equal(report.d.recommendations.length, 3);
  report.d.recommendations.forEach((action) => {
    assert.ok(action.deep_link && action.deep_link.startsWith('../'));
    assert.ok(action.reason.length > 0);
  });
});

test('recommendations priority 1 targets the weakest topic', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      // fraction-word-g5: 5 wrong, high hint
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 3 },
      { ts: Date.parse('2026-03-15T08:10:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 3 },
      { ts: Date.parse('2026-03-15T08:20:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T08:30:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T08:40:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 1 },
      // volume-g5: 1 wrong
      { ts: Date.parse('2026-03-15T09:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: false, max_hint: 1 },
    ],
    practiceEvents: []
  });

  // Top recommendation should target fraction-word-g5 (most wrong + highest hint dependency)
  assert.ok(
    report.d.recommendations[0].deep_link.includes('fraction'),
    'Priority 1 recommendation should target the weakest topic (fraction)'
  );
});

test('recommendations include action_text for each entry', () => {
  const report = windowObj.AIMathReportDataBuilder.buildReportData({
    name: 'Kai',
    days: 7,
    nowMs: Date.parse('2026-03-16T12:00:00Z'),
    attempts: [
      { ts: Date.parse('2026-03-15T08:00:00Z'), unit_id: 'fraction-word-g5', kind: 'addition', ok: false, max_hint: 2 },
      { ts: Date.parse('2026-03-15T09:00:00Z'), unit_id: 'volume-g5', kind: 'rect_cm3', ok: false, max_hint: 1 },
    ],
    practiceEvents: []
  });

  report.d.recommendations.forEach((action, i) => {
    assert.ok(action.action_text && action.action_text.length > 5,
      `Recommendation ${i + 1} must have actionable text, got: "${action.action_text}"`);
    assert.ok(action.concept && action.concept.length > 0,
      `Recommendation ${i + 1} must have a concept label`);
  });
});

test('recommendations produce stable links for known topics', () => {
  const engine = windowObj.AIMathRecommendationEngine;
  const knownTopics = [
    'fraction-word-g5', 'fraction-g5', 'volume-g5',
    'interactive-decimal-g5', 'ratio-percent-g5'
  ];
  knownTopics.forEach(topic => {
    const link = engine.getTopicLink(topic);
    assert.ok(link.includes(topic.split('-')[0]) || link !== '../star-pack/',
      `known topic "${topic}" should resolve to a non-fallback link`);
  });
});

test('deeper weakness and remedial cards reuse the shared evidence formatter', () => {
  const src = fs.readFileSync(path.resolve('docs/parent-report/index.html'), 'utf8');
  assert.ok(src.includes('${esc(weaknessEvidenceText(w))}'), 'weakness table should use the shared evidence formatter');
  assert.ok(src.includes('evidenceText: weaknessEvidenceText(w)'), 'remedial recommendations should store shared evidence text');
  assert.ok(src.includes("esc(rec.evidenceText || '')"), 'remedial cards should render the shared evidence text');
  assert.ok(!src.includes('提示≥L2：${(w.h2 || 0) + (w.h3 || 0)} 次'), 'inline weakness evidence formatting should be removed to avoid drift');
});
