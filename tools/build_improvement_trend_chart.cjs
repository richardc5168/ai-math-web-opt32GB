const fs = require('fs');
const path = require('path');

function readJson(filePath, fallback = {}) {
  if (!fs.existsSync(filePath)) return fallback;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readJsonl(filePath) {
  if (!fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function writeJsonl(filePath, rows) {
  const text = rows.map((row) => JSON.stringify(row)).join('\n') + '\n';
  fs.writeFileSync(filePath, text, 'utf8');
}

function isoDate(input) {
  return new Date(input).toISOString().slice(0, 10);
}

const cwd = process.cwd();
const artifactsDir = path.join(cwd, 'artifacts');
const historyRepoPath = path.join(cwd, 'golden', 'improvement_trend_history.jsonl');
const historyArtifactPath = path.join(artifactsDir, 'improvement_trend_history.jsonl');
const trendJsonPath = path.join(artifactsDir, 'improvement_trend.json');
const trendMdPath = path.join(artifactsDir, 'improvement_trend.md');
const webTrendDocsPath = path.join(cwd, 'docs', 'improvement', 'latest.json');
const webTrendDistPath = path.join(cwd, 'dist_ai_math_web_pages', 'docs', 'improvement', 'latest.json');

const hintJudge = readJson(path.join(artifactsDir, 'hint_judge.json'), { summary: { avg_score: 0, min_score: 0 } });
const scorecard = readJson(path.join(artifactsDir, 'scorecard.json'), { e2e: { flaky_rate: 1 } });

const today = new Date();
const todayIso = isoDate(today);
const point = {
  date: todayIso,
  hint_avg: Number(hintJudge.summary?.avg_score || 0),
  hint_min: Number(hintJudge.summary?.min_score || 0),
  e2e_flaky_rate: Number(scorecard.e2e?.flaky_rate ?? 1),
};

const history = readJsonl(historyRepoPath);
const withoutToday = history.filter((row) => isoDate(row.date || todayIso) !== todayIso);
const nextHistory = [...withoutToday, point].sort((a, b) => String(a.date).localeCompare(String(b.date)));

const prevPoint = nextHistory.length >= 2 ? nextHistory[nextHistory.length - 2] : null;
const deltas = {
  hint_avg: prevPoint ? Number((point.hint_avg - Number(prevPoint.hint_avg || 0)).toFixed(2)) : 0,
  hint_min: prevPoint ? Number((point.hint_min - Number(prevPoint.hint_min || 0)).toFixed(2)) : 0,
  e2e_flaky_rate: prevPoint ? Number((point.e2e_flaky_rate - Number(prevPoint.e2e_flaky_rate || 0)).toFixed(4)) : 0,
};

const improvedPoints = [];
if (deltas.hint_avg > 0) improvedPoints.push(`hint_avg 提升 +${deltas.hint_avg}`);
if (deltas.hint_min > 0) improvedPoints.push(`hint_min 提升 +${deltas.hint_min}`);
if (deltas.e2e_flaky_rate < 0) improvedPoints.push(`e2e_flaky_rate 下降 ${deltas.e2e_flaky_rate}`);
if (improvedPoints.length === 0) improvedPoints.push('本次無明顯提升（持平或微幅波動）');

fs.mkdirSync(artifactsDir, { recursive: true });
writeJsonl(historyArtifactPath, nextHistory);
writeJsonl(historyRepoPath, nextHistory);
fs.writeFileSync(trendJsonPath, JSON.stringify({ points: nextHistory }, null, 2), 'utf8');

const webPayload = {
  generated_at: new Date().toISOString(),
  current: point,
  previous: prevPoint,
  delta: deltas,
  improved_points: improvedPoints,
  points: nextHistory,
};
fs.mkdirSync(path.dirname(webTrendDocsPath), { recursive: true });
fs.mkdirSync(path.dirname(webTrendDistPath), { recursive: true });
fs.writeFileSync(webTrendDocsPath, JSON.stringify(webPayload, null, 2), 'utf8');
fs.writeFileSync(webTrendDistPath, JSON.stringify(webPayload, null, 2), 'utf8');

const labels = nextHistory.map((row) => row.date);
const avgSeries = nextHistory.map((row) => row.hint_avg);
const minSeries = nextHistory.map((row) => row.hint_min);
const flakySeries = nextHistory.map((row) => Number((row.e2e_flaky_rate * 100).toFixed(2)));

const md = [
  '# Improvement Trend (Daily)',
  '',
  `Generated at: ${new Date().toISOString()}`,
  '',
  '## Metrics',
  `- hint avg: ${point.hint_avg}`,
  `- hint min: ${point.hint_min}`,
  `- e2e flaky rate: ${point.e2e_flaky_rate}`,
  '',
  '## Trend Chart',
  '```mermaid',
  'xychart-beta',
  '  title "Hint / E2E Daily Trend"',
  `  x-axis [${labels.map((v) => `"${v}"`).join(', ')}]`,
  '  y-axis "hint score" 0 --> 10',
  `  line "hint_avg" [${avgSeries.join(', ')}]`,
  `  line "hint_min" [${minSeries.join(', ')}]`,
  '```',
  '',
  '```mermaid',
  'xychart-beta',
  '  title "E2E Flaky Rate (%)"',
  `  x-axis [${labels.map((v) => `"${v}"`).join(', ')}]`,
  '  y-axis "percent" 0 --> 100',
  `  line "flaky_rate_pct" [${flakySeries.join(', ')}]`,
  '```',
  '',
].join('\n');

fs.writeFileSync(trendMdPath, md, 'utf8');
console.log(`trend chart generated: ${trendMdPath}`);
