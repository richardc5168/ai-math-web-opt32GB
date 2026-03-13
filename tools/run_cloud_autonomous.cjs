/**
 * Cloud Autonomous Optimizer
 *
 * Designed for GitHub Actions — runs optimization phases from ops/agent_tasks.json,
 * auto-commits with rollback tags, writes status to ops/agent_status.json.
 *
 * Key differences from run_12h_autonomous.cjs:
 *   - Reads task queue from ops/agent_tasks.json (editable from GitHub web UI)
 *   - Creates git tags before changes for instant rollback
 *   - Writes live status to ops/agent_status.json (visible on GitHub)
 *   - Supports phase_sequence tasks (pipeline, hints, content, validate, commit)
 *   - Optimized for GitHub Actions 6-hour timeout
 *
 * Usage:
 *   node tools/run_cloud_autonomous.cjs                   # default 4h
 *   node tools/run_cloud_autonomous.cjs --hours 6         # max GA timeout
 *   node tools/run_cloud_autonomous.cjs --once            # single pass
 *   node tools/run_cloud_autonomous.cjs --dry-run         # no git ops
 */

const fs = require('fs');
const path = require('path');
const { runCommand, pythonCmd } = require('./_runner.cjs');

// ── CLI ───────────────────────────────────────────────────

function argValue(name, fb) {
  const i = process.argv.indexOf(name);
  return (i >= 0 && i + 1 < process.argv.length) ? process.argv[i + 1] : fb;
}
function hasFlag(name) { return process.argv.includes(name); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const MAX_HOURS    = Number(argValue('--hours', '4'));
const INTERVAL_MIN = Number(argValue('--interval-min', '20'));
const ONCE         = hasFlag('--once');
const DRY_RUN      = hasFlag('--dry-run');
const NO_PUSH      = hasFlag('--no-push');
const py           = pythonCmd();

// ── Paths ─────────────────────────────────────────────────

const TASKS_PATH   = path.join(process.cwd(), 'ops', 'agent_tasks.json');
const STATUS_PATH  = path.join(process.cwd(), 'ops', 'agent_status.json');
const STATE_PATH   = path.join(process.cwd(), 'ops', 'agent_tasks_state.json');
const HISTORY_PATH = path.join(process.cwd(), 'artifacts', 'cloud_autonomous_history.jsonl');
const HEARTBEAT_PATH = path.join(process.cwd(), 'artifacts', 'cloud_autonomous_heartbeat.json');

// ── Helpers ───────────────────────────────────────────────

function ts() { return new Date().toISOString(); }

function ensureDir(rel) {
  const p = path.join(process.cwd(), rel);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

function readJson(fpath, fallback) {
  if (!fs.existsSync(fpath)) return fallback;
  try { return JSON.parse(fs.readFileSync(fpath, 'utf8')); }
  catch { return fallback; }
}

function writeJson(fpath, data) {
  fs.mkdirSync(path.dirname(fpath), { recursive: true });
  fs.writeFileSync(fpath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function appendJsonl(fpath, entry) {
  fs.mkdirSync(path.dirname(fpath), { recursive: true });
  fs.appendFileSync(fpath, JSON.stringify(entry) + '\n', 'utf8');
}

function writeHeartbeat(payload) {
  try { writeJson(HEARTBEAT_PATH, { at: ts(), ...payload }); } catch (_) {}
}

function runStep(cmd, args, logs, label, timeoutSec = 1800) {
  writeHeartbeat({ status: 'running_step', step: label });
  console.log(`    ▶ ${label} (timeout ${timeoutSec}s)`);
  const res = runCommand(cmd, args, { timeout: timeoutSec * 1000 });
  logs.push({ time: ts(), step: label, pass: res.pass, status: res.status, timedOut: Boolean(res.timedOut) });
  if (!res.pass) console.log(`    ✖ ${label} failed`);
  return res;
}

// ── Schedule helpers ──────────────────────────────────────

const SCHEDULE_INTERVALS = {
  'every_30m':  30,
  'every_1h':   60,
  'every_2h':   120,
  'every_4h':   240,
  'every_6h':   360,
  'every_8h':   480,
  'every_12h':  720,
  'every_24h':  1440,
};

function shouldRun(task, state, nowMs) {
  if (!task || !task.enabled) return false;
  const intervalMin = SCHEDULE_INTERVALS[task.schedule] || 240;
  const lastRun = state.last_run_at?.[task.id];
  if (!lastRun) return true;
  const elapsed = (nowMs - Date.parse(lastRun)) / 60000;
  return elapsed >= intervalMin;
}

// ── Rollback tag ──────────────────────────────────────────

function createRollbackTag(taskId) {
  if (DRY_RUN) return null;
  const tag = `rollback/${taskId}/${new Date().toISOString().replace(/[:.]/g, '-')}`;
  const res = runCommand('git', ['tag', tag]);
  if (res.pass) {
    console.log(`    🏷 Created rollback tag: ${tag}`);
    return tag;
  }
  return null;
}

function rollback(tag, taskId) {
  if (DRY_RUN || !tag) return;
  console.log(`    ⏪ Rolling back to tag: ${tag}`);
  runCommand('git', ['reset', '--hard', tag]);
  runCommand('git', ['clean', '-fd', '--', 'golden/', 'docs/improvement/', 'dist_ai_math_web_pages/docs/improvement/']);
}

// ── Phase runners ─────────────────────────────────────────

function phasePipeline(logs) {
  console.log('  [Phase: pipeline] OER → generate → solve → verify');
  const res = runStep(py, ['-m', 'pipeline.auto_pipeline', '--offline'], logs, 'pipeline:generate', 600);
  return res.pass;
}

function phaseHints(logs) {
  console.log('  [Phase: hints] autotune → judge → scorecard → gate');
  const steps = [
    ['npm', ['run', 'autotune:hints'], 'autotune:hints'],
    ['npm', ['run', 'judge:hints'], 'judge:hints'],
    ['npm', ['run', 'scorecard'], 'scorecard'],
    ['npm', ['run', 'gate:scorecard'], 'gate:scorecard'],
  ];
  for (const [cmd, args, label] of steps) {
    const res = runStep(cmd, args, logs, label);
    if (!res.pass) return false;
  }
  return true;
}

function phaseContent(logs) {
  console.log('  [Phase: content] web-search → report-signals → topic-align');
  const steps = [
    ['npm', ['run', 'agent:web-search'], 'web-search'],
    ['npm', ['run', 'derive:report-signals'], 'derive:report-signals'],
    ['npm', ['run', 'apply:report-signals'], 'apply:report-signals'],
    ['npm', ['run', 'topic:align'], 'topic:align'],
    ['npm', ['run', 'fraction-decimal:web:ingest'], 'fraction-decimal:ingest'],
    ['npm', ['run', 'fraction-decimal:web:build'], 'fraction-decimal:build'],
    ['npm', ['run', 'fraction-decimal:web:validate'], 'fraction-decimal:validate'],
  ];
  let allOk = true;
  for (const [cmd, args, label] of steps) {
    const res = runStep(cmd, args, logs, label);
    if (!res.pass) {
      console.log(`    ⚠ ${label} failed (non-fatal)`);
      allOk = false;
    }
  }
  return allOk;
}

function phaseValidate(logs) {
  console.log('  [Phase: validate] verify:all → elementary banks → quality gate → diagram audit');
  const v1 = runStep('npm', ['run', 'verify:all'], logs, 'verify:all');
  if (!v1.pass) return false;
  const v2 = runStep(py, ['tools/validate_all_elementary_banks.py'], logs, 'validate_elementary_banks');
  if (!v2.pass) return false;
  const quality = runStep('npm', ['run', 'quality:nightly:gate'], logs, 'quality:nightly:gate');
  if (!quality.pass) return false;
  // Diagram audit (non-fatal)
  runStep('node', ['tools/audit_hint_diagrams.cjs'], logs, 'audit:diagrams');
  // Improvement trend
  const diffGolden = runCommand('git', ['diff', '--quiet', '--', 'golden/grade5_pack_v1.jsonl']);
  const mode = diffGolden.pass ? 'enforce' : 'require-improvement';
  runStep('node', ['tools/check_improvement_trend.cjs', '--mode', mode], logs, 'improvement:trend');
  return true;
}

function phaseSelfHeal(logs) {
  console.log('  [Phase: self-heal] fix + verify');
  runStep('npm', ['run', 'self-heal:verify'], logs, 'self-heal');
  runStep('npm', ['run', 'memory:update'], logs, 'memory:update');
}

// ── Commit with rollback safety ───────────────────────────

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
  'ops/agent_status.json',
  'ops/agent_tasks_state.json',
];

function phaseCommit(taskId, iteration, logs) {
  console.log('  [Phase: commit] stage → commit → push');
  if (DRY_RUN) {
    logs.push({ time: ts(), step: 'commit', pass: true, status: 0, note: 'dry-run' });
    return { committed: false, pushed: false, hash: null };
  }

  // Stage tracked files
  runCommand('git', ['add', '--', ...TRACKED_PATHS]);
  const hasStagedRes = runCommand('git', ['diff', '--cached', '--quiet']);
  if (hasStagedRes.pass) {
    console.log('    ℹ no staged changes');
    return { committed: false, pushed: false, hash: null };
  }

  const msg = `chore: cloud autonomous — ${taskId} (iteration ${iteration})`;
  let commitRes = runCommand('git', ['commit', '--no-verify', '-m', msg]);
  if (!commitRes.pass) {
    // Retry once
    runCommand('git', ['add', '--', ...TRACKED_PATHS]);
    commitRes = runCommand('git', ['commit', '--no-verify', '-m', msg]);
  }
  logs.push({ time: ts(), step: 'commit', pass: commitRes.pass, status: commitRes.status });

  if (!commitRes.pass) return { committed: false, pushed: false, hash: null };

  const hashRes = runCommand('git', ['rev-parse', '--short', 'HEAD']);
  const hash = hashRes.pass ? (hashRes.stdout || '').trim() : null;

  let pushed = false;
  if (!NO_PUSH) {
    const pushRes = runCommand('git', ['push', 'origin', 'main']);
    pushed = pushRes.pass;
    logs.push({ time: ts(), step: 'push', pass: pushRes.pass, status: pushRes.status });

    // Also push to appmirror if configured
    const remotesRes = runCommand('git', ['remote']);
    if (remotesRes.pass && remotesRes.stdout.includes('appmirror')) {
      const appPush = runCommand('git', ['push', 'appmirror', 'main']);
      logs.push({ time: ts(), step: 'push:appmirror', pass: appPush.pass, status: appPush.status });
    }
  }

  return { committed: true, pushed, hash };
}

// ── Task executor ─────────────────────────────────────────

const PHASE_RUNNERS = {
  pipeline: phasePipeline,
  hints: phaseHints,
  content: phaseContent,
  validate: phaseValidate,
};

function executeTask(task, iteration, logs) {
  if (task.action === 'npm_script') {
    const script = String(task.value || '').trim();
    console.log(`  [Task: ${task.id}] npm run ${script}`);
    const timeoutSec = (task.timeout_min || 30) * 60;
    const res = runStep('npm', ['run', script], logs, `npm:${script}`, timeoutSec);
    return res.pass;
  }

  if (task.action === 'shell') {
    const cmd = String(task.value || '').trim();
    console.log(`  [Task: ${task.id}] shell: ${cmd}`);
    const parts = cmd.split(/\s+/);
    const timeoutSec = (task.timeout_min || 30) * 60;
    const res = runStep(parts[0], parts.slice(1), logs, `shell:${task.id}`, timeoutSec);
    return res.pass;
  }

  if (task.action === 'phase_sequence') {
    const phases = task.phases || [];
    console.log(`  [Task: ${task.id}] phases: ${phases.join(' → ')}`);

    // Create rollback tag
    const rollbackTag = createRollbackTag(task.id);

    let overallPass = true;
    for (const phase of phases) {
      if (phase === 'commit') {
        // Commit phase handled separately
        if (overallPass) {
          const commitResult = phaseCommit(task.id, iteration, logs);
          logs.push({ time: ts(), step: 'phase:commit', pass: true, committed: commitResult.committed, hash: commitResult.hash });
        }
        continue;
      }

      if (phase === 'validate') {
        const ok = phaseValidate(logs);
        if (!ok) {
          console.log('  ⚠ Validation failed — attempting self-heal...');
          phaseSelfHeal(logs);
          const retry = phaseValidate(logs);
          if (!retry) {
            overallPass = false;
            // Rollback if configured
            const config = readJson(TASKS_PATH, {}).config || {};
            if (config.auto_rollback && rollbackTag) {
              rollback(rollbackTag, task.id);
            }
            break;
          }
        }
        continue;
      }

      const runner = PHASE_RUNNERS[phase];
      if (!runner) {
        console.log(`  ⚠ Unknown phase: ${phase}`);
        continue;
      }

      const ok = runner(logs);
      if (!ok && phase !== 'content') {
        // content is non-fatal
        overallPass = false;
        break;
      }
    }

    return overallPass;
  }

  console.log(`  ⚠ Unknown action: ${task.action}`);
  return false;
}

// ── Status writer ─────────────────────────────────────────

function writeStatus(update) {
  const existing = readJson(STATUS_PATH, {});
  const status = {
    ...existing,
    ...update,
    updated_at: ts(),
  };
  writeJson(STATUS_PATH, status);
}

function commitStatus() {
  if (DRY_RUN) return;
  runCommand('git', ['add', 'ops/agent_status.json', 'ops/agent_tasks_state.json']);
  const hasStagedRes = runCommand('git', ['diff', '--cached', '--quiet']);
  if (!hasStagedRes.pass) {
    runCommand('git', ['commit', '--no-verify', '-m', 'chore: update agent status']);
    if (!NO_PUSH) {
      runCommand('git', ['push', 'origin', 'main']);
    }
  }
}

// ── Main loop ─────────────────────────────────────────────

async function main() {
  const startTime = Date.now();
  const endAt = startTime + Math.max(0.5, MAX_HOURS) * 3600 * 1000;
  const intervalMs = Math.max(1, INTERVAL_MIN) * 60 * 1000;

  ensureDir('artifacts');
  ensureDir('artifacts/cloud_iterations');

  console.log(`\n${'='.repeat(60)}`);
  console.log('  CLOUD AUTONOMOUS OPTIMIZER');
  console.log(`  Hours: ${MAX_HOURS} | Interval: ${INTERVAL_MIN}min | Push: ${!NO_PUSH} | DryRun: ${DRY_RUN}`);
  console.log(`  Tasks file: ${TASKS_PATH}`);
  console.log(`  Started: ${ts()}`);
  console.log(`  Will stop at: ${new Date(endAt).toISOString()}`);
  console.log(`${'='.repeat(60)}\n`);

  // Pull latest
  if (!DRY_RUN) {
    const pull = runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
    console.log(`git pull: ${pull.pass ? 'OK' : 'SKIP'}`);
  }

  let iteration = 0;
  let totalTasksRun = 0;
  let totalCommits = 0;
  let consecutiveFailures = 0;
  let lastStatusCommit = 0;

  const runPass = async () => {
    iteration++;
    const iterStart = ts();
    console.log(`\n--- Iteration ${iteration} started: ${iterStart} ---`);

    // Reload tasks (may have been updated remotely)
    if (!DRY_RUN) {
      runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
    }

    const tasksConfig = readJson(TASKS_PATH, { tasks: [], config: {} });
    const tasks = (tasksConfig.tasks || []).filter(t => t && t.enabled);
    const state = readJson(STATE_PATH, { last_run_at: {}, results: {} });
    const nowMs = Date.now();

    // Sort by priority
    tasks.sort((a, b) => (a.priority || 99) - (b.priority || 99));

    // Find tasks due to run
    const due = tasks.filter(t => shouldRun(t, state, nowMs));
    console.log(`  Tasks total: ${tasks.length}, due: ${due.length}`);

    writeStatus({
      mode: 'running',
      iteration,
      started_at: iterStart,
      tasks_total: tasks.length,
      tasks_due: due.length,
      total_tasks_run: totalTasksRun,
      total_commits: totalCommits,
    });

    if (due.length === 0) {
      console.log('  No tasks due — idle');
      writeHeartbeat({ status: 'idle', iteration });

      // Run idle expansion if available
      const idleRes = runCommand('npm', ['run', 'idle:web:fraction-decimal:expand'], { timeout: 300000 });
      if (idleRes.pass) {
        const validateOk = phaseValidate([]);
        if (validateOk) {
          phaseCommit('idle-expand', iteration, []);
        }
      }

      return;
    }

    for (const task of due) {
      if (Date.now() >= endAt) {
        console.log('  ⏰ Time limit reached, stopping');
        break;
      }

      const taskStart = ts();
      const logs = [];
      console.log(`\n  ═══ Task: ${task.id} (priority ${task.priority || '?'}) ═══`);
      console.log(`  ${task.description || ''}`);

      writeStatus({
        current_task: task.id,
        current_task_started: taskStart,
        current_task_description: task.description,
      });
      writeHeartbeat({ status: 'running_task', task: task.id, iteration });

      const ok = executeTask(task, iteration, logs);

      // Record result
      state.last_run_at = state.last_run_at || {};
      state.last_run_at[task.id] = taskStart;
      state.results = state.results || {};
      state.results[task.id] = {
        last_run: taskStart,
        last_result: ok ? 'pass' : 'fail',
        last_duration_sec: Math.round((Date.now() - Date.parse(taskStart)) / 1000),
      };
      writeJson(STATE_PATH, state);

      if (ok) {
        totalTasksRun++;
        consecutiveFailures = 0;
      } else {
        consecutiveFailures++;
        if (consecutiveFailures >= (tasksConfig.config?.max_consecutive_failures || 5)) {
          console.log(`  ✖ ${consecutiveFailures} consecutive failures — stopping`);
          break;
        }
      }

      // Append to history
      appendJsonl(HISTORY_PATH, {
        iteration,
        task_id: task.id,
        started_at: taskStart,
        finished_at: ts(),
        pass: ok,
        logs,
      });

      console.log(`  ═══ Task ${task.id}: ${ok ? '✔ PASS' : '✖ FAIL'} ═══`);
    }

    // Write summaries
    try {
      runCommand('npm', ['run', 'summary:iteration'], { timeout: 60000 });
      runCommand('npm', ['run', 'summary:kpi'], { timeout: 60000 });
    } catch (_) {}

    // Periodic status commit
    const statusInterval = (tasksConfig.config?.status_commit_interval_min || 60) * 60000;
    if (Date.now() - lastStatusCommit > statusInterval) {
      writeStatus({
        mode: 'running',
        iteration,
        total_tasks_run: totalTasksRun,
        total_commits: totalCommits,
        consecutive_failures: consecutiveFailures,
        runtime_hours: ((Date.now() - startTime) / 3600000).toFixed(2),
      });
      commitStatus();
      lastStatusCommit = Date.now();
    }
  };

  if (ONCE) {
    await runPass();
  } else {
    while (Date.now() < endAt) {
      try {
        await runPass();
      } catch (err) {
        console.error('Iteration error:', err);
        appendJsonl(HISTORY_PATH, { iteration, error: String(err?.message || err), at: ts() });
      }

      if (Date.now() + intervalMs >= endAt) break;

      // Adaptive backoff
      let sleepMs = intervalMs;
      if (consecutiveFailures >= 3) {
        sleepMs = Math.min(intervalMs * 2, 3600000);
        console.log(`  ⚠ ${consecutiveFailures} failures — backing off to ${Math.round(sleepMs / 60000)}min`);
      }

      console.log(`  Sleep ${Math.round(sleepMs / 60000)} minutes...`);
      writeHeartbeat({ status: 'sleeping', iteration, next_at: new Date(Date.now() + sleepMs).toISOString() });
      await sleep(sleepMs);
    }
  }

  // Final status
  const finalReport = {
    mode: 'finished',
    finished_at: ts(),
    runtime_hours: ((Date.now() - startTime) / 3600000).toFixed(2),
    total_iterations: iteration,
    total_tasks_run: totalTasksRun,
    total_commits: totalCommits,
    consecutive_failures: consecutiveFailures,
    dry_run: DRY_RUN,
  };

  writeStatus(finalReport);
  writeJson(path.join(process.cwd(), 'artifacts', 'cloud_autonomous_summary.json'), finalReport);
  writeHeartbeat({ status: 'finished', ...finalReport });

  // Final status commit
  commitStatus();

  console.log(`\n${'='.repeat(60)}`);
  console.log('  CLOUD AUTONOMOUS OPTIMIZER — COMPLETE');
  console.log(JSON.stringify(finalReport, null, 2));
  console.log(`${'='.repeat(60)}\n`);
}

main().catch(err => { console.error(err); process.exit(1); });
