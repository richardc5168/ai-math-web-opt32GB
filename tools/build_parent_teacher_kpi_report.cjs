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

function readLastJsonl(relPath, maxLines = 800) {
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

function pct(value) {
  const n = Number(value || 0);
  return `${(n * 100).toFixed(1)}%`;
}

function clamp01(v) {
  const n = Number(v || 0);
  if (!Number.isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

function round2(v) {
  return Math.round(Number(v || 0) * 100) / 100;
}

const scorecard = readJson('artifacts/scorecard.json', {});
const hintJudge = readJson('artifacts/hint_judge.json', { summary: {} });
const hintSummary = readJson('artifacts/hint_optimization_summary.json', {});
const iterSummary = readJson('artifacts/iteration_output_summary.json', {});
const heartbeat = readJson('artifacts/autonomous_heartbeat.json', {});
const latestCmd = readJson('artifacts/hourly_command_latest.json', {});
const runs = readLastJsonl('artifacts/hourly_command_runs.jsonl', 1200);

const last30mMs = Date.now() - (30 * 60 * 1000);
const recentRuns = runs.filter((r) => Date.parse(String(r.ended_at || r.started_at || '')) >= last30mMs);
const recentPass = recentRuns.filter((r) => r.pass).length;
const recentTotal = recentRuns.length;
const recentPassRate = recentTotal > 0 ? recentPass / recentTotal : 1;

const hintAvg = Number(hintJudge?.summary?.avg_score || 0);
const hintMin = Number(hintJudge?.summary?.min_score || 0);
const hintCount = Number(hintJudge?.summary?.count || 0);
const autotuneChanged = Number(iterSummary?.optimization?.hint_autotune_changed || hintSummary?.hint_optimization?.autotune_changed || 0);

const scorecardPass = Boolean(scorecard?.tests?.pass);
const goldenCorrect = clamp01(scorecard?.golden?.correct_rate || 0);
const e2eFlaky = clamp01(scorecard?.e2e?.flaky_rate ?? 1);
const a11y = clamp01(scorecard?.lighthouse?.accessibility || 0);
const performance = clamp01(scorecard?.lighthouse?.performance || 0);

const stabilityScore = clamp01((goldenCorrect * 0.5) + ((1 - e2eFlaky) * 0.3) + (scorecardPass ? 0.2 : 0));
const clarityScore = clamp01((hintAvg / 5) * 0.7 + (hintMin / 5) * 0.3);
const uxScore = clamp01((a11y * 0.6) + (performance * 0.4));
const executionScore = clamp01(recentPassRate);

const parentTeacherKPI = {
  generated_at: new Date().toISOString(),
  objective: 'parent_teacher_buy_in_for_elementary_math_quality',
  quality_gate: {
    scorecard_pass: scorecardPass,
    golden_correct_rate: round2(goldenCorrect),
    e2e_flaky_rate: round2(e2eFlaky),
    hint_avg_score: round2(hintAvg),
    hint_min_score: round2(hintMin),
    hint_count: hintCount,
    hint_autotune_changed: autotuneChanged,
  },
  operational_health_30m: {
    run_count: recentTotal,
    pass_count: recentPass,
    pass_rate: round2(recentPassRate),
    latest_command_id: latestCmd?.id || null,
    latest_command_pass: typeof latestCmd?.pass === 'boolean' ? latestCmd.pass : null,
    autonomous_heartbeat_status: heartbeat?.status || null,
    autonomous_heartbeat_at: heartbeat?.at || null,
  },
  kpi_scores: {
    stability: round2(stabilityScore),
    hint_clarity: round2(clarityScore),
    user_experience: round2(uxScore),
    automation_execution: round2(executionScore),
  },
  buy_in_summary: {
    readiness: (stabilityScore >= 0.9 && clarityScore >= 0.85 && executionScore >= 0.8) ? 'strong' : (stabilityScore >= 0.8 ? 'watch' : 'improve'),
    messages: [
      scorecardPass ? '核心測試門檻通過，可維持家長信任。' : '測試門檻未全過，需先穩定再擴充。',
      hintAvg >= 4 ? '提示平均分高，教師可直接用於課堂引導。' : '提示清晰度需持續優化（先改善低分題型）。',
      recentPassRate >= 0.8 ? '30 分鐘自動回圈穩定，適合無人值守。' : '自動流程成功率偏低，建議調整指令節奏或重試策略。'
    ]
  },
  links: {
    scorecard: 'artifacts/scorecard.json',
    hint_judge: 'artifacts/hint_judge.json',
    hint_summary: 'artifacts/hint_optimization_summary.json',
    iteration_summary: 'artifacts/iteration_output_summary.json',
    hourly_runs: 'artifacts/hourly_command_runs.jsonl',
    heartbeat: 'artifacts/autonomous_heartbeat.json'
  }
};

const md = [
  '# Parent & Teacher KPI (30min)',
  '',
  `- generated_at: ${parentTeacherKPI.generated_at}`,
  `- readiness: ${parentTeacherKPI.buy_in_summary.readiness}`,
  '',
  '## Quality Gate',
  `- scorecard_pass: ${parentTeacherKPI.quality_gate.scorecard_pass}`,
  `- golden_correct_rate: ${pct(parentTeacherKPI.quality_gate.golden_correct_rate)}`,
  `- e2e_flaky_rate: ${pct(parentTeacherKPI.quality_gate.e2e_flaky_rate)}`,
  `- hint_avg_score: ${parentTeacherKPI.quality_gate.hint_avg_score}`,
  `- hint_min_score: ${parentTeacherKPI.quality_gate.hint_min_score}`,
  `- hint_autotune_changed: ${parentTeacherKPI.quality_gate.hint_autotune_changed}`,
  '',
  '## Automation Health (Last 30min)',
  `- run_count: ${parentTeacherKPI.operational_health_30m.run_count}`,
  `- pass_rate: ${pct(parentTeacherKPI.operational_health_30m.pass_rate)}`,
  `- latest_command_id: ${parentTeacherKPI.operational_health_30m.latest_command_id}`,
  `- autonomous_heartbeat_status: ${parentTeacherKPI.operational_health_30m.autonomous_heartbeat_status}`,
  `- autonomous_heartbeat_at: ${parentTeacherKPI.operational_health_30m.autonomous_heartbeat_at}`,
  '',
  '## KPI Scores',
  `- stability: ${pct(parentTeacherKPI.kpi_scores.stability)}`,
  `- hint_clarity: ${pct(parentTeacherKPI.kpi_scores.hint_clarity)}`,
  `- user_experience: ${pct(parentTeacherKPI.kpi_scores.user_experience)}`,
  `- automation_execution: ${pct(parentTeacherKPI.kpi_scores.automation_execution)}`,
  '',
  '## Buy-in Messages',
  ...parentTeacherKPI.buy_in_summary.messages.map((m) => `- ${m}`),
  '',
].join('\n');

fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'parent_teacher_kpi.json'), JSON.stringify(parentTeacherKPI, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'parent_teacher_kpi.md'), md, 'utf8');

console.log(JSON.stringify({
  summary: 'parent teacher kpi generated',
  json: 'artifacts/parent_teacher_kpi.json',
  md: 'artifacts/parent_teacher_kpi.md',
  readiness: parentTeacherKPI.buy_in_summary.readiness,
  stability: parentTeacherKPI.kpi_scores.stability,
  hint_clarity: parentTeacherKPI.kpi_scores.hint_clarity,
  automation_execution: parentTeacherKPI.kpi_scores.automation_execution
}, null, 2));
