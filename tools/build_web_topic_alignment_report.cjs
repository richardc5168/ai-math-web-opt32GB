const fs = require('fs');
const path = require('path');

function readJson(filePath, fallback = null) {
  if (!fs.existsSync(filePath)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

const root = process.cwd();
const cfgPath = path.join(root, 'golden', 'external_math_topic_alignment.json');
const cfg = readJson(cfgPath, { topic_map: [], sources: [] });

const docsRoot = path.join(root, 'docs');
const docsEntries = fs.existsSync(docsRoot)
  ? fs
      .readdirSync(docsRoot, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
  : [];

const topics = Array.isArray(cfg.topic_map) ? cfg.topic_map : [];
const rows = topics.map((t) => {
  const modules = Array.isArray(t.repo_modules) ? t.repo_modules : [];
  const covered = modules.filter((m) => docsEntries.includes(m));
  const missing = modules.filter((m) => !docsEntries.includes(m));
  return {
    topic: t.topic,
    grades: t.grades || [],
    covered_modules: covered,
    missing_modules: missing,
    coverage_rate: modules.length ? Number((covered.length / modules.length).toFixed(2)) : 0,
    hint_focus: t.hint_focus || [],
  };
});

const coverageAvg = rows.length
  ? Number((rows.reduce((acc, r) => acc + Number(r.coverage_rate || 0), 0) / rows.length).toFixed(2))
  : 0;

const report = {
  generated_at: new Date().toISOString(),
  sources: cfg.sources || [],
  topics: rows,
  summary: {
    topic_count: rows.length,
    avg_coverage_rate: coverageAvg,
    fully_covered_topics: rows.filter((r) => r.coverage_rate >= 1).map((r) => r.topic),
    partial_topics: rows.filter((r) => r.coverage_rate < 1).map((r) => r.topic),
  },
};

const artifactsDir = path.join(root, 'artifacts');
fs.mkdirSync(artifactsDir, { recursive: true });
const jsonOut = path.join(artifactsDir, 'web_topic_alignment.json');
const mdOut = path.join(artifactsDir, 'web_topic_alignment.md');
fs.writeFileSync(jsonOut, JSON.stringify(report, null, 2) + '\n', 'utf8');

const md = [
  '# Web Topic Alignment Report',
  '',
  `- generated_at: ${report.generated_at}`,
  `- topic_count: ${report.summary.topic_count}`,
  `- avg_coverage_rate: ${report.summary.avg_coverage_rate}`,
  '',
  '## Sources',
  ...(report.sources.length ? report.sources.map((s) => `- ${s.name}: ${s.url}`) : ['- none']),
  '',
  '## Topics',
  ...rows.map((r) => `- ${r.topic}: coverage=${r.coverage_rate}, covered=[${r.covered_modules.join(', ')}], missing=[${r.missing_modules.join(', ')}]`),
  '',
].join('\n');
fs.writeFileSync(mdOut, md, 'utf8');

console.log(JSON.stringify({ path_json: 'artifacts/web_topic_alignment.json', path_md: 'artifacts/web_topic_alignment.md', avg_coverage_rate: coverageAvg }, null, 2));
