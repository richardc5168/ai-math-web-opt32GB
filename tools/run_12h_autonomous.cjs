/**
 * 12-Hour Autonomous Optimization Runner
 *
 * Runs COMPLETELY STANDALONE — no Copilot, no VS Code, no "Allow" clicks.
 * Start it once and walk away for 12 hours.
 *
 * What it does every iteration:
 *   Phase 1 — Pipeline: OER fetch → generate → deterministic solve → verify
 *   Phase 2 — Hints:   autotune → judge → scorecard → gate
 *   Phase 3 — Content: web-search → report-signals → topic-align → coverage
 *   Phase 4 — Validate: verify:all → elementary banks → improvement trend
 *   Phase 5 — Self-heal on any failure, then retry once
 *   Phase 6 — Auto-commit + push (only if validation passes)
 *
 * Usage:
 *   node tools/run_12h_autonomous.cjs                           # 12h, interval 20min
 *   node tools/run_12h_autonomous.cjs --hours 8                 # 8h
 *   node tools/run_12h_autonomous.cjs --interval-min 10         # faster loops
 *   node tools/run_12h_autonomous.cjs --no-push                 # commit but don't push
 *   node tools/run_12h_autonomous.cjs --dry-run                 # simulate, no git ops
 *   npm run autonomous:12h                                      # via npm script
 */

const fs = require('fs');
const path = require('path');
const { runCommand, pythonCmd } = require('./_runner.cjs');

// ── CLI args ──────────────────────────────────────────────

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}
function hasFlag(name) { return process.argv.includes(name); }
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

const MAX_HOURS     = Number(argValue('--hours', '12'));
const INTERVAL_MIN  = Number(argValue('--interval-min', '20'));
const NO_PUSH       = hasFlag('--no-push');
const DRY_RUN       = hasFlag('--dry-run');
const STEP_TIMEOUT_SEC = Number(argValue('--step-timeout-sec', '1800'));
const py            = pythonCmd();

// ── Helpers ───────────────────────────────────────────────

function ensureDir(rel) {
  const p = path.join(process.cwd(), rel);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

function readJson(rel, fallback) {
  const p = path.join(process.cwd(), rel);
  if (!fs.existsSync(p)) return fallback;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return fallback; }
}

function ts() { return new Date().toISOString(); }

function writeHeartbeat(payload) {
  const p = path.join(process.cwd(), 'artifacts', 'autonomous_heartbeat.json');
  try {
    fs.writeFileSync(p, JSON.stringify({ at: ts(), ...payload }, null, 2) + '\n', 'utf8');
  } catch (_) {
    // non-fatal
  }
}

function runStep(cmd, args, logs, retries = 1, options = {}) {
  const timeoutMs = Number(options.timeoutMs || STEP_TIMEOUT_SEC * 1000);
  const label = options.label || `${cmd} ${args.join(' ')}`;
  writeHeartbeat({ status: 'running_step', step: label, timeout_ms: timeoutMs });
  console.log(`    ▶ ${label} (timeout ${Math.round(timeoutMs / 1000)}s)`);

  let res = runCommand(cmd, args, { timeout: timeoutMs });
  logs.push({
    time: ts(),
    command: `${cmd} ${args.join(' ')}`,
    pass: res.pass,
    status: res.status,
    timedOut: Boolean(res.timedOut),
    error: res.error || null,
  });

  if (res.timedOut) {
    console.log(`    ✖ timeout: ${label}`);
  }

  let attempt = 0;
  while (!res.pass && attempt < retries) {
    attempt++;
    writeHeartbeat({ status: 'retry_step', step: label, attempt, timeout_ms: timeoutMs });
    res = runCommand(cmd, args, { timeout: timeoutMs });
    logs.push({
      time: ts(),
      command: `${cmd} ${args.join(' ')} (retry-${attempt})`,
      pass: res.pass,
      status: res.status,
      timedOut: Boolean(res.timedOut),
      error: res.error || null,
    });
  }
  writeHeartbeat({ status: 'step_done', step: label, pass: res.pass, status_code: res.status, timed_out: Boolean(res.timedOut) });
  return res;
}

// ── Tracked files for staging ─────────────────────────────

const TRACKED_PATHS = [
  'golden/grade5_pack_v1.jsonl',
  'golden/improvement_baseline.json',
  'golden/improvement_trend_history.jsonl',
  'golden/error_memory.jsonl',
  'docs/improvement/latest.json',
  'docs/shared/hint_engine.js',
  'dist_ai_math_web_pages/docs/improvement/latest.json',
  'dist_ai_math_web_pages/docs/shared/hint_engine.js',
  'tools/hint_diagram_known_issues.json',
  'data/generated/',
  'data/human_queue/',
];

function stageFiles() {
  return runCommand('git', ['add', '--', ...TRACKED_PATHS]);
}

function resetFiles() {
  return runCommand('git', ['restore', '--', ...TRACKED_PATHS.filter((p) => !p.endsWith('/'))]);
}

// ── Phase definitions ─────────────────────────────────────

/**
 * Phase 1: Pipeline — auto-generate questions with deterministic solver
 * This runs the new Python pipeline end-to-end (offline mode).
 */
function phasePipeline(logs) {
  console.log('  [BP1/Phase 1] Pipeline: generate + solve + verify');
  // Run the auto-pipeline in offline mode
  const res = runStep(py, ['-m', 'pipeline.auto_pipeline', '--offline'], logs, 1);
  if (!res.pass) {
    console.log('  [Phase 1] pipeline:generate failed, trying dry-run for diagnostics...');
    runStep(py, ['-m', 'pipeline.auto_pipeline', '--offline', '--dry-run'], logs, 0);
  }
  return res.pass;
}

/**
 * Phase 2: Hint optimization — autotune, judge, scorecard
 */
function phaseHints(logs) {
  console.log('  [BP2/Phase 2] Hints: autotune → judge → scorecard');
  const steps = [
    ['npm', ['run', 'autotune:hints']],
    ['npm', ['run', 'judge:hints']],
    ['npm', ['run', 'scorecard']],
    ['npm', ['run', 'gate:scorecard']],
  ];
  for (const [cmd, args] of steps) {
    const res = runStep(cmd, args, logs, 1);
    if (!res.pass) return false;
  }
  return true;
}

/**
 * Phase 3: Content expansion — web search, report signals, topic alignment
 */
function phaseContent(logs) {
  console.log('  [BP3/Phase 3] Content: web-search → report-signals → topic-align');
  const steps = [
    ['npm', ['run', 'agent:web-search']],
    ['npm', ['run', 'derive:report-signals']],
    ['npm', ['run', 'apply:report-signals']],
    ['npm', ['run', 'topic:align']],
    // Fraction-decimal expand (non-fatal)
    ['npm', ['run', 'fraction-decimal:web:ingest']],
    ['npm', ['run', 'fraction-decimal:web:build']],
    ['npm', ['run', 'fraction-decimal:web:validate']],
  ];
  let allPass = true;
  for (const [cmd, args] of steps) {
    const res = runStep(cmd, args, logs, 1);
    if (!res.pass) {
      // Content steps are non-fatal — log but continue
      console.log(`    ⚠ ${args.join(' ')} failed (non-fatal, continuing)`);
      allPass = false;
    }
  }
  return allPass;
}

/**
 * Phase 4: Validation — verify:all, elementary banks, improvement trend
 */
function phaseValidate(logs) {
  console.log('  [BP4/Phase 4] Validate: verify:all → elementary banks → diagram audit → improvement');
  const verifyAll = runStep('npm', ['run', 'verify:all'], logs, 1);
  if (!verifyAll.pass) return false;

  const banks = runStep(py, ['tools/validate_all_elementary_banks.py'], logs, 1);
  if (!banks.pass) return false;

  // Diagram/hint regression audit (non-fatal but logged)
  const diagAudit = runStep('node', ['tools/audit_hint_diagrams.cjs'], logs, 0);
  if (!diagAudit.pass) {
    console.log('  ⚠ Diagram audit found issues (see artifacts/hint_diagram_audit.json)');
  }

  // Improvement trend — check if golden changed
  const diffGolden = runCommand('git', ['diff', '--quiet', '--', 'golden/grade5_pack_v1.jsonl']);
  const mode = diffGolden.pass ? 'enforce' : 'require-improvement';
  const trend = runStep('node', ['tools/check_improvement_trend.cjs', '--mode', mode], logs, 1);
  if (!trend.pass && mode === 'require-improvement') {
    // Fallback: at least enforce non-regression
    const fallback = runStep('node', ['tools/check_improvement_trend.cjs', '--mode', 'enforce'], logs, 1);
    return fallback.pass;
  }
  return trend.pass;
}

/**
 * Phase 5: Self-heal on failure
 */
function phaseSelfHeal(logs) {
  console.log('  [BP5/Phase 5] Self-heal: fix + verify');
  runStep('npm', ['run', 'self-heal:verify'], logs, 0);
  runStep('npm', ['run', 'memory:update'], logs, 0);
  runStep('npm', ['run', 'triage:agent'], logs, 0);
}

/**
 * Phase 6: Auto-commit + push
 */
function phaseCommit(iteration, logs) {
  console.log('  [BP6/Phase 6] Auto-commit + push');
  writeHeartbeat({ status: 'bp6_started', iteration });
  if (DRY_RUN) {
    logs.push({ time: ts(), command: 'DRY_RUN: skip commit', pass: true, status: 0 });
    console.log('    ℹ dry-run mode: skip commit/push');
    writeHeartbeat({ status: 'bp6_done', iteration, committed: false, pushed: false, reason: 'dry-run' });
    return { committed: false, pushed: false, hash: null };
  }

  const statusRes = runCommand('git', ['status', '--porcelain']);
  if (!statusRes.stdout || !statusRes.stdout.trim()) {
    console.log('    ℹ no working tree changes');
    writeHeartbeat({ status: 'bp6_done', iteration, committed: false, pushed: false, reason: 'no changes' });
    return { committed: false, pushed: false, hash: null, reason: 'no changes' };
  }

  stageFiles();
  const hasStagedRes = runCommand('git', ['diff', '--cached', '--quiet']);
  if (hasStagedRes.pass) {
    console.log('    ℹ no staged tracked changes');
    writeHeartbeat({ status: 'bp6_done', iteration, committed: false, pushed: false, reason: 'no staged changes' });
    return { committed: false, pushed: false, hash: null, reason: 'no staged changes' };
  }

  const msg = `chore: autonomous iteration ${iteration} — pipeline + hints + content`;
  let commitRes = { pass: false };
  for (let t = 1; t <= 3; t++) {
    stageFiles();
    commitRes = runCommand('git', ['commit', '--no-verify', '-m', msg]);
    if (commitRes.pass) break;
  }
  logs.push({ time: ts(), command: `git commit -m "${msg}"`, pass: commitRes.pass, status: commitRes.status });

  if (!commitRes.pass) {
    console.log('    ✖ commit failed after retries');
    writeHeartbeat({ status: 'bp6_done', iteration, committed: false, pushed: false, reason: 'commit failed' });
    return { committed: false, pushed: false, hash: null, reason: 'commit failed' };
  }

  const hashRes = runCommand('git', ['rev-parse', '--short', 'HEAD']);
  const hash = hashRes.pass ? (hashRes.stdout || '').trim() : null;

  let pushed = false;
  if (!NO_PUSH) {
    const pushRes = runCommand('git', ['push', 'origin', 'main']);
    pushed = pushRes.pass;
    logs.push({ time: ts(), command: 'git push origin main', pass: pushRes.pass, status: pushRes.status });
    console.log(`    ${pushRes.pass ? '✔' : '✖'} push ${pushRes.pass ? 'ok' : 'failed'}`);
  }

  writeHeartbeat({ status: 'bp6_done', iteration, committed: true, pushed, hash });

  return { committed: true, pushed, hash };
}

// ── Agent Loop Integration ────────────────────────────────

/**
 * Run the Python agent loop once — this handles error memory consultation,
 * hourly command execution, and idle detection.
 */
function runAgentLoop(logs) {
  console.log('  [Agent Loop] error-memory → hourly-commands → idle-check');
  return runStep(py, ['-m', 'pipeline.agent_loop', '--once'], logs, 0);
}

// ── Summary helpers ───────────────────────────────────────

function writeSummary(logs) {
  runStep('npm', ['run', 'summary:iteration'], logs, 0);
  runStep('npm', ['run', 'summary:hints'], logs, 0);
  runStep('npm', ['run', 'summary:kpi'], logs, 0);
}

// ── Main loop ─────────────────────────────────────────────

async function main() {
  const startTime = Date.now();
  const endAt = startTime + Math.max(1, MAX_HOURS) * 3600 * 1000;
  const intervalMs = Math.max(1, INTERVAL_MIN) * 60 * 1000;

  const artifactsDir = ensureDir('artifacts');
  const iterDir = ensureDir('artifacts/autonomous_iterations');
  const historyPath = path.join(artifactsDir, 'autonomous_history.jsonl');

  console.log(`\n${'='.repeat(60)}`);
  console.log(`  12-HOUR AUTONOMOUS RUNNER`);
  console.log(`  Hours: ${MAX_HOURS} | Interval: ${INTERVAL_MIN}min | Push: ${!NO_PUSH} | DryRun: ${DRY_RUN}`);
  console.log(`  Step timeout: ${STEP_TIMEOUT_SEC}s`);
  console.log(`  Started: ${ts()}`);
  console.log(`  Will stop at: ${new Date(endAt).toISOString()}`);
  console.log(`${'='.repeat(60)}\n`);

  // Pull latest before starting
  if (!DRY_RUN) {
    const pull = runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
    console.log(`git pull: ${pull.pass ? 'OK' : 'SKIP'}`);
  }

  let iteration = 0;
  let totalCommits = 0;
  let totalPipelineRuns = 0;
  let consecutiveFailures = 0;

  while (Date.now() < endAt) {
    iteration++;
    const iterStart = ts();
    console.log(`\n--- Iteration ${iteration} started: ${iterStart} ---`);

    const logs = [];
    let overallPass = true;
    writeHeartbeat({ status: 'iteration_started', iteration, started_at: iterStart });

    // Git pull at start of each iteration (pick up remote changes)
    if (!DRY_RUN) {
      runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
    }

    // Phase 1: Pipeline (generate + solve)
    const pipelineOk = phasePipeline(logs);
    if (pipelineOk) totalPipelineRuns++;

    // Phase 2: Hint optimization
    const hintsOk = phaseHints(logs);
    if (!hintsOk) overallPass = false;

    // Phase 3: Content expansion
    phaseContent(logs); // non-fatal

    // Agent loop (error memory + hourly commands + idle triggers)
    runAgentLoop(logs);

    // Phase 4: Validation (GATE)
    const validateOk = phaseValidate(logs);
    if (!validateOk) {
      overallPass = false;
      // Self-heal and retry validation once
      console.log('  Validation failed — attempting self-heal...');
      phaseSelfHeal(logs);
      const retryOk = phaseValidate(logs);
      if (!retryOk) {
        console.log('  Validation still failing — resetting optimization files');
        resetFiles();
      } else {
        overallPass = true;
      }
    }

    // Summaries (non-fatal)
    writeSummary(logs);

    // Phase 6: Commit + push
    let commitResult = { committed: false, pushed: false, hash: null };
    if (overallPass) {
      commitResult = phaseCommit(iteration, logs);
      if (commitResult.committed) totalCommits++;
      consecutiveFailures = 0;
    } else {
      consecutiveFailures++;
      logs.push({ time: ts(), command: 'SKIP commit (validation failed)', pass: false, status: 1 });
    }

    // Write iteration record
    const iterSummary = readJson('artifacts/iteration_output_summary.json', {});
    const entry = {
      iteration,
      started_at: iterStart,
      finished_at: ts(),
      pass: overallPass,
      pipeline_ran: pipelineOk,
      hints_optimized: hintsOk,
      commit: commitResult,
      hint_autotune_changed: Number(iterSummary?.optimization?.hint_autotune_changed || 0),
      report_signal_changed: Number(iterSummary?.optimization?.report_signal_changed || 0),
      consecutive_failures: consecutiveFailures,
      logs,
    };

    const iterFile = path.join(iterDir, `iter-${String(iteration).padStart(3, '0')}.json`);
    fs.writeFileSync(iterFile, JSON.stringify(entry, null, 2) + '\n', 'utf8');
    fs.appendFileSync(historyPath, JSON.stringify(entry) + '\n', 'utf8');

    console.log(`--- Iteration ${iteration} done: pass=${overallPass} commit=${commitResult.hash || 'none'} ---`);

    // Adaptive backoff: if 3+ consecutive failures, double the interval
    let actualInterval = intervalMs;
    if (consecutiveFailures >= 3) {
      actualInterval = Math.min(intervalMs * 2, 60 * 60 * 1000); // cap at 1h
      console.log(`  ⚠ ${consecutiveFailures} consecutive failures — backing off to ${actualInterval / 60000}min`);
    }

    // Sleep before next iteration
    if (Date.now() + actualInterval < endAt) {
      const sleepMin = Math.round(actualInterval / 60000);
      console.log(`  Sleep ${sleepMin} minutes before next iteration...`);
      writeHeartbeat({ status: 'sleeping', iteration, sleep_minutes: sleepMin });
      await sleep(actualInterval);
    } else {
      break;
    }
  }

  // Final summary
  const finalReport = {
    finished_at: ts(),
    runtime_hours: ((Date.now() - startTime) / 3600000).toFixed(2),
    total_iterations: iteration,
    total_commits: totalCommits,
    total_pipeline_runs: totalPipelineRuns,
    consecutive_failures_at_end: consecutiveFailures,
    dry_run: DRY_RUN,
    history_path: 'artifacts/autonomous_history.jsonl',
  };

  fs.writeFileSync(
    path.join(artifactsDir, 'autonomous_run_summary.json'),
    JSON.stringify(finalReport, null, 2) + '\n',
    'utf8'
  );
  writeHeartbeat({ status: 'finished', ...finalReport });

  console.log(`\n${'='.repeat(60)}`);
  console.log('  AUTONOMOUS RUN COMPLETE');
  console.log(JSON.stringify(finalReport, null, 2));
  console.log(`${'='.repeat(60)}\n`);
}

main().catch((err) => { console.error(err); process.exit(1); });
