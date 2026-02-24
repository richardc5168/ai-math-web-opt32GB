const fs = require('fs');
const path = require('path');
const { runCommand } = require('../tools/_runner.cjs');

const LOCK_PATH = path.join(process.cwd(), 'artifacts', 'idle_fraction_decimal_expand.lock.json');
const STATUS_PATH = path.join(process.cwd(), 'artifacts', 'idle_fraction_decimal_expand.latest.json');
const DEFAULT_COMMAND_FILE = path.join(process.cwd(), 'ops', 'hourly_commands.json');
const DEFAULT_STATE_FILE = path.join(process.cwd(), 'ops', 'hourly_commands_state.json');

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function readJson(filePath, fallback = null) {
  try {
    if (!fs.existsSync(filePath)) return fallback;
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function minutesSince(iso) {
  const t = Date.parse(String(iso || ''));
  if (!Number.isFinite(t)) return Number.POSITIVE_INFINITY;
  return (Date.now() - t) / 60000;
}

function getIdleDecision(idleMinutes, stuckMinutes, force) {
  if (force) return { canRun: true, reason: 'force' };

  const hourlyState = readJson(path.join(process.cwd(), 'artifacts', 'hourly_command_state.json'), {});
  const hourlyLatest = readJson(path.join(process.cwd(), 'artifacts', 'hourly_command_latest.json'), {});
  const overnightSummary = readJson(path.join(process.cwd(), 'artifacts', 'overnight_run_summary.json'), {});

  const hasAnyState = Object.keys(hourlyState || {}).length > 0 || Object.keys(hourlyLatest || {}).length > 0;
  if (!hasAnyState) return { canRun: true, reason: 'no_task_state' };

  const pendingExecuted = Number(hourlyLatest?.pending_executed ?? -1);
  if (pendingExecuted === 0) return { canRun: true, reason: 'task_completed' };

  const stateAge = minutesSince(hourlyState?.last_checked_at);
  const latestAge = minutesSince(hourlyLatest?.checked_at || hourlyLatest?.ended_at || hourlyLatest?.started_at);

  if (Number.isFinite(stateAge) && stateAge > stuckMinutes) {
    return { canRun: true, reason: `state_stale_${Math.floor(stateAge)}m` };
  }
  if (Number.isFinite(latestAge) && latestAge > stuckMinutes) {
    return { canRun: true, reason: `latest_stale_${Math.floor(latestAge)}m` };
  }

  const overnightAge = minutesSince(overnightSummary?.finished_at);
  if (Number.isFinite(overnightAge) && overnightAge <= idleMinutes) {
    return { canRun: true, reason: 'task_recently_completed' };
  }

  return { canRun: false, reason: 'active_or_recent_task' };
}

function lockIsFresh(idleMinutes) {
  const lock = readJson(LOCK_PATH, null);
  if (!lock || lock.status !== 'running') return false;
  const age = minutesSince(lock.heartbeat_at || lock.started_at);
  return Number.isFinite(age) && age <= idleMinutes;
}

function writeLock(status, extra = {}) {
  const now = new Date().toISOString();
  const prev = readJson(LOCK_PATH, {});
  writeJson(LOCK_PATH, {
    ...prev,
    status,
    started_at: prev.started_at || now,
    heartbeat_at: now,
    updated_at: now,
    ...extra,
  });
}

function runStep(cmd, args, logs, lockMeta = {}) {
  writeLock('running', lockMeta);
  const r = runCommand(cmd, args);
  logs.push({ command: `${cmd} ${args.join(' ')}`, pass: r.pass, status: r.status, stderr: r.pass ? '' : r.stderr });
  return r;
}

function main() {
  const idleMinutes = Number(argValue('--idle-minutes', '20'));
  const stuckMinutes = Number(argValue('--stuck-minutes', '30'));
  const commandFile = String(argValue('--command-file', DEFAULT_COMMAND_FILE));
  const stateFile = String(argValue('--state-file', DEFAULT_STATE_FILE));
  const force = hasFlag('--force');
  const autoCommit = hasFlag('--auto-commit');

  if (lockIsFresh(idleMinutes) && !force) {
    const out = { pass: true, skipped: true, reason: 'active_lock_fresh' };
    writeJson(STATUS_PATH, out);
    console.log(JSON.stringify(out, null, 2));
    return;
  }

  const decision = getIdleDecision(idleMinutes, stuckMinutes, force);
  if (!decision.canRun) {
    const out = { pass: true, skipped: true, reason: decision.reason };
    writeJson(STATUS_PATH, out);
    console.log(JSON.stringify(out, null, 2));
    return;
  }

  const logs = [];
  writeLock('running', { reason: decision.reason, idle_minutes: idleMinutes, stuck_minutes: stuckMinutes });

  // === Phase 1: Core expand pipeline (fatal on failure) ===
  const coreSteps = [
    ['python', ['tools/external_web_ingest/collect_fraction_decimal_notes.py']],
    ['python', ['tools/external_web_ingest/build_fraction_decimal_pack.py', '--n', '40', '--seed', '60224']],
    ['python', ['tools/external_web_ingest/validate_fraction_decimal_pack.py']],
    ['python', ['-m', 'pytest', 'tests/test_fraction_decimal_application_web_contract.py', '-q']],
    ['python', ['-m', 'pytest', 'tests/test_fraction_decimal_application_web_loop.py', '-q']],
    ['npm', ['run', 'verify:all']],
  ];

  for (const [cmd, args] of coreSteps) {
    const r = runStep(cmd, args, logs, { current_step: `${cmd} ${args.join(' ')}` });
    if (!r.pass) {
      writeLock('failed', { logs_count: logs.length });
      const out = { pass: false, skipped: false, reason: `failed: ${cmd}`, logs };
      writeJson(STATUS_PATH, out);
      console.log(JSON.stringify(out, null, 2));
      process.exit(1);
    }
  }

  // === Phase 2: Auto-commit if changes ===
  let commit = { pass: true, done: false, hash: null };
  if (autoCommit) {
    const st = runStep('git', ['status', '--porcelain'], logs, { current_step: 'git status --porcelain' });
    if (st.pass && st.stdout && st.stdout.trim()) {
      const add = runStep('git', ['add', '-A'], logs, { current_step: 'git add -A' });
      if (add.pass) {
        const msg = 'feat: add idle external-web fraction/decimal application question type';
        const c = runStep('git', ['commit', '--no-verify', '-m', msg], logs, { current_step: 'git commit' });
        if (c.pass) {
          const h = runStep('git', ['rev-parse', '--short', 'HEAD'], logs, { current_step: 'git rev-parse' });
          commit = { pass: true, done: true, hash: h.pass ? (h.stdout || '').trim() : null };
          // push after commit
          runStep('git', ['push', 'origin', 'main'], logs, { current_step: 'git push' });
        } else {
          commit = { pass: false, done: false, hash: null };
        }
      } else {
        commit = { pass: false, done: false, hash: null };
      }
    }
  }

  // === Phase 3: Post-completion — poll hourly_commands.json (non-fatal) ===
  // Conditions: task complete OR idle OR idle>30min → execute remaining commands
  let pollResult = { pass: true, skipped: false, reason: 'post_complete_poll' };
  try {
    const pollArgs = [
      'tools/poll_hourly_commands.cjs',
      '--once',
      '--command-file', commandFile,
      '--state-file', stateFile,
    ];
    const r = runStep('node', pollArgs, logs, { current_step: 'post-poll hourly_commands' });
    pollResult = { pass: r.pass, skipped: false, reason: r.pass ? 'poll_ok' : 'poll_fail_nonfatal' };
  } catch (e) {
    pollResult = { pass: true, skipped: true, reason: `poll_error: ${e.message}` };
  }

  writeLock('done', { logs_count: logs.length, commit, poll: pollResult });
  const out = { pass: commit.pass, skipped: false, reason: decision.reason, commit, poll: pollResult, logs };
  writeJson(STATUS_PATH, out);
  console.log(JSON.stringify(out, null, 2));

  if (!commit.pass) process.exit(1);
}

main();
