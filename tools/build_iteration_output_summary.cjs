const fs = require('fs');
const path = require('path');

function readJson(relPath, fallback = null) {
  const p = path.join(process.cwd(), relPath);
  if (!fs.existsSync(p)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return fallback;
  }
}

function fileExists(relPath) {
  return fs.existsSync(path.join(process.cwd(), relPath));
}

const autotune = readJson('artifacts/autotune_report.json', { changed: 0, touched: [] });
const reportApply = readJson('artifacts/report_autotune_apply.json', { changed: 0, touched_ids: [] });
const hintJudge = readJson('artifacts/hint_judge.json', { summary: { avg_score: 0, min_score: 0, count: 0 } });
const scorecard = readJson('artifacts/scorecard.json', null);
const improvement = readJson('artifacts/improvement_check.json', null);
const trend = readJson('artifacts/improvement_trend.json', { points: [] });
const triage = readJson('artifacts/agent_triage.json', null);
const topicAlign = readJson('artifacts/web_topic_alignment.json', null);

const summary = {
  generated_at: new Date().toISOString(),
  objective: {
    optimize_question_and_hints: true,
    optimize_parent_report: true,
    optimize_user_experience: true,
  },
  optimization: {
    hint_autotune_changed: Number(autotune?.changed || 0),
    hint_autotune_touched: Array.isArray(autotune?.touched) ? autotune.touched.slice(0, 30) : [],
    report_signal_changed: Number(reportApply?.changed || 0),
    report_signal_touched: Array.isArray(reportApply?.touched_ids) ? reportApply.touched_ids.slice(0, 30) : [],
  },
  quality: {
    scorecard_ok: !!(scorecard && scorecard.tests?.pass),
    hint_avg: Number(hintJudge?.summary?.avg_score || 0),
    hint_min: Number(hintJudge?.summary?.min_score || 0),
    hint_count: Number(hintJudge?.summary?.count || 0),
    golden_correct_rate: Number(scorecard?.golden?.correct_rate || 0),
    e2e_flaky_rate: Number(scorecard?.e2e?.flaky_rate ?? 1),
    lighthouse_accessibility: Number(scorecard?.lighthouse?.accessibility || 0),
    lighthouse_performance: Number(scorecard?.lighthouse?.performance || 0),
    axe_critical: Number(scorecard?.axe?.critical || 0),
  },
  improvement: {
    non_regression: improvement ? !!improvement.non_regression : null,
    improved: improvement ? !!improvement.improved : null,
    mode: improvement?.mode || null,
    latest_trend_point: Array.isArray(trend?.points) && trend.points.length ? trend.points[trend.points.length - 1] : null,
  },
  diagnostics: {
    likely_root_cause: triage?.likely_root_cause || 'unknown',
    failed_checks: Array.isArray(triage?.failed_checks) ? triage.failed_checks : [],
    topic_alignment_avg_coverage: Number(topicAlign?.summary?.avg_coverage_rate || 0),
  },
  artifact_links: {
    autotune_report: 'artifacts/autotune_report.json',
    report_autotune_apply: 'artifacts/report_autotune_apply.json',
    hint_judge: 'artifacts/hint_judge.json',
    scorecard: 'artifacts/scorecard.json',
    improvement_check: 'artifacts/improvement_check.json',
    trend_json: 'artifacts/improvement_trend.json',
    trend_md: 'artifacts/improvement_trend.md',
    triage_json: 'artifacts/agent_triage.json',
    triage_md: 'artifacts/agent_triage.md',
    topic_alignment_json: 'artifacts/web_topic_alignment.json',
    topic_alignment_md: 'artifacts/web_topic_alignment.md',
  },
};

const md = [
  '# Iteration Output Summary',
  '',
  `- generated_at: ${summary.generated_at}`,
  '',
  '## Optimization',
  `- hint_autotune_changed: ${summary.optimization.hint_autotune_changed}`,
  `- report_signal_changed: ${summary.optimization.report_signal_changed}`,
  '',
  '## Quality',
  `- scorecard_ok: ${summary.quality.scorecard_ok}`,
  `- hint_avg: ${summary.quality.hint_avg}`,
  `- hint_min: ${summary.quality.hint_min}`,
  `- golden_correct_rate: ${summary.quality.golden_correct_rate}`,
  `- e2e_flaky_rate: ${summary.quality.e2e_flaky_rate}`,
  `- lighthouse_accessibility: ${summary.quality.lighthouse_accessibility}`,
  `- lighthouse_performance: ${summary.quality.lighthouse_performance}`,
  `- axe_critical: ${summary.quality.axe_critical}`,
  '',
  '## Improvement',
  `- non_regression: ${summary.improvement.non_regression}`,
  `- improved: ${summary.improvement.improved}`,
  `- mode: ${summary.improvement.mode}`,
  '',
  '## Topic Alignment',
  `- avg_coverage_rate: ${summary.diagnostics.topic_alignment_avg_coverage}`,
  '',
  '## Artifact Paths',
  ...Object.values(summary.artifact_links)
    .filter((p) => fileExists(p))
    .map((p) => `- ${p}`),
  '',
].join('\n');

fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'iteration_output_summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'iteration_output_summary.md'), md, 'utf8');

console.log(
  JSON.stringify(
    {
      summary: 'iteration output summary generated',
      path_json: 'artifacts/iteration_output_summary.json',
      path_md: 'artifacts/iteration_output_summary.md',
      hint_autotune_changed: summary.optimization.hint_autotune_changed,
      report_signal_changed: summary.optimization.report_signal_changed,
      improved: summary.improvement.improved,
      non_regression: summary.improvement.non_regression,
    },
    null,
    2
  )
);
