const fs = require('fs');
const path = require('path');
const TOP_N = 10;

function readJson(relPath, fallback = null) {
  const p = path.join(process.cwd(), relPath);
  if (!fs.existsSync(p)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return fallback;
  }
}

function readLastJsonl(relPath, maxLines = 400) {
  const p = path.join(process.cwd(), relPath);
  if (!fs.existsSync(p)) return [];
  const raw = fs.readFileSync(p, 'utf8').trim();
  if (!raw) return [];
  const lines = raw.split(/\r?\n/).filter(Boolean);
  return lines.slice(-maxLines).map((line) => {
    try {
      return JSON.parse(line);
    } catch {
      return null;
    }
  }).filter(Boolean);
}

function latestById(items, id) {
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (items[i] && String(items[i].id || '') === id) return items[i];
  }
  return null;
}

function inferTopic(id) {
  const v = String(id || '').toLowerCase();
  if (v.includes('frac')) return 'fraction';
  if (v.includes('ratio') || v.includes('percent')) return 'ratio_percent';
  if (v.includes('decimal')) return 'decimal';
  if (v.includes('volume')) return 'volume';
  if (v.includes('average')) return 'average';
  if (v.includes('discount')) return 'discount';
  return 'general';
}

function buildRecommendation(item) {
  const topic = inferTopic(item?.id);
  const notes = Array.isArray(item?.notes) ? item.notes : [];
  const actions = [];

  if (notes.length) {
    actions.push(`Address detected issue: ${notes[0]}`);
  }

  actions.push('Keep Level 3 as guided reasoning steps only, never reveal final numeric answer.');

  if (topic === 'fraction') {
    actions.push('Clarify whole-vs-remainder base before multiplying fractions.');
  } else if (topic === 'ratio_percent') {
    actions.push('State ratio/percent reference quantity explicitly before conversion.');
  } else if (topic === 'decimal') {
    actions.push('Separate place-value reasoning from arithmetic execution in two short steps.');
  } else if (topic === 'volume') {
    actions.push('Require unit check before and after formula substitution.');
  } else {
    actions.push('Add one misconception check sentence before final computation step.');
  }

  return {
    id: item?.id || 'unknown',
    topic,
    score: Number(item?.score || 0),
    actions: actions.slice(0, 3)
  };
}

const hintJudge = readJson('artifacts/hint_judge.json', { summary: { avg_score: 0, min_score: 0, count: 0 }, items: [] });
const autotune = readJson('artifacts/autotune_report.json', { changed: 0, touched: [] });
const runs = readLastJsonl('artifacts/hourly_command_runs_10h_auto.jsonl', 500);

const runHintJudge = latestById(runs, '2026-02-27-hint-judge-30m');
const runAutotune = latestById(runs, '2026-02-27-hint-autotune-30m');
const runSummary = latestById(runs, '2026-02-26-summary-30m');
const runMail = latestById(runs, '2026-02-26-status-mail-30m');

const topItems = Array.isArray(hintJudge.items)
  ? hintJudge.items
      .slice()
      .sort((a, b) => Number(a.score || 0) - Number(b.score || 0))
      .slice(0, TOP_N)
      .map((item) => ({
        id: item.id,
        score: Number(item.score || 0),
        notes: Array.isArray(item.notes) ? item.notes : [],
      }))
  : [];

const recommendations = topItems.map((item) => buildRecommendation(item));

const summary = {
  generated_at: new Date().toISOString(),
  hint_quality: {
    avg_score: Number(hintJudge?.summary?.avg_score || 0),
    min_score: Number(hintJudge?.summary?.min_score || 0),
    count: Number(hintJudge?.summary?.count || 0),
    lowest_items: topItems,
    top_n: TOP_N,
  },
  hint_optimization: {
    autotune_changed: Number(autotune?.changed || 0),
    autotune_touched: Array.isArray(autotune?.touched) ? autotune.touched.slice(0, 40) : [],
  },
  latest_30m_cycle: {
    summary_iteration: runSummary ? { pass: !!runSummary.pass, ended_at: runSummary.ended_at || null } : null,
    status_mail: runMail ? { pass: !!runMail.pass, ended_at: runMail.ended_at || null, reason: runMail.reason || '' } : null,
    hint_judge: runHintJudge ? { pass: !!runHintJudge.pass, ended_at: runHintJudge.ended_at || null, reason: runHintJudge.reason || '' } : null,
    hint_autotune: runAutotune ? { pass: !!runAutotune.pass, ended_at: runAutotune.ended_at || null, reason: runAutotune.reason || '' } : null,
  },
  recommendations,
  notes: [
    'Level 3 hints must guide and never expose final answer directly.',
    'When wording includes "remaining" or "of the remainder", change the reference base explicitly before operations.'
  ],
  artifact_links: {
    hint_judge: 'artifacts/hint_judge.json',
    autotune_report: 'artifacts/autotune_report.json',
    iteration_output_summary: 'artifacts/iteration_output_summary.json',
    hourly_runs: 'artifacts/hourly_command_runs_10h_auto.jsonl'
  }
};

const md = [
  '# Teaching Hint Optimization Summary',
  '',
  `- generated_at: ${summary.generated_at}`,
  `- hint_avg_score: ${summary.hint_quality.avg_score}`,
  `- hint_min_score: ${summary.hint_quality.min_score}`,
  `- hint_item_count: ${summary.hint_quality.count}`,
  `- autotune_changed: ${summary.hint_optimization.autotune_changed}`,
  '',
  '## Latest 30m Cycle',
  `- summary_iteration_pass: ${summary.latest_30m_cycle.summary_iteration?.pass ?? null}`,
  `- status_mail_pass: ${summary.latest_30m_cycle.status_mail?.pass ?? null}`,
  `- hint_judge_pass: ${summary.latest_30m_cycle.hint_judge?.pass ?? null}`,
  `- hint_autotune_pass: ${summary.latest_30m_cycle.hint_autotune?.pass ?? null}`,
  '',
  '## Lowest Hint Score Items (Top 10)',
  ...summary.hint_quality.lowest_items.map((item) => `- ${item.id}: score=${item.score}`),
  '',
  '## Improvement Recommendations',
  ...summary.recommendations.flatMap((rec) => [
    `- ${rec.id} [${rec.topic}] score=${rec.score}`,
    ...rec.actions.map((action) => `  - ${action}`)
  ]),
  '',
  '## Notes',
  ...summary.notes.map((note) => `- ${note}`),
  '',
].join('\n');

fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'hint_optimization_summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'hint_optimization_summary.md'), md, 'utf8');

console.log(JSON.stringify({
  summary: 'hint optimization summary generated',
  json: 'artifacts/hint_optimization_summary.json',
  md: 'artifacts/hint_optimization_summary.md',
  hint_avg_score: summary.hint_quality.avg_score,
  hint_min_score: summary.hint_quality.min_score,
  autotune_changed: summary.hint_optimization.autotune_changed
}, null, 2));
