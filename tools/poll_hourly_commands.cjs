const fs = require('fs');
const path = require('path');
const { runCommand, pythonCmd } = require('./_runner.cjs');

const COMMAND_FILE_DEFAULT = path.join(process.cwd(), 'ops', 'hourly_commands.json');
const STATE_PATH = path.join(process.cwd(), 'artifacts', 'hourly_command_state.json');
const RUN_LOG_PATH = path.join(process.cwd(), 'artifacts', 'hourly_command_runs.jsonl');
const LATEST_STATUS_PATH = path.join(process.cwd(), 'artifacts', 'hourly_command_latest.json');

const ALLOWED_NPM_SCRIPTS = new Set([
  'verify:all',
  'topic:align',
  'summary:iteration',
  'triage:agent',
  'memory:update',
  'judge:hints',
  'scorecard',
  'trend:improvement',
  'gate:scorecard'
]);

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ensureArtifacts() {
  const p = path.join(process.cwd(), 'artifacts');
  fs.mkdirSync(p, { recursive: true });
}

function readState() {
  if (!fs.existsSync(STATE_PATH)) return { executed_ids: [] };
  try {
    return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
  } catch {
    return { executed_ids: [] };
  }
}

function writeState(state) {
  ensureArtifacts();
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + '\n', 'utf8');
}

function appendRunLog(entry) {
  ensureArtifacts();
  fs.appendFileSync(RUN_LOG_PATH, `${JSON.stringify(entry)}\n`, 'utf8');
}

function writeLatestStatus(status) {
  ensureArtifacts();
  fs.writeFileSync(LATEST_STATUS_PATH, JSON.stringify(status, null, 2) + '\n', 'utf8');
}

function normalizeCommands(payload) {
  if (!payload || !Array.isArray(payload.commands)) return [];
  return payload.commands.filter((c) => c && typeof c.id === 'string');
}

function readCommandFile(commandFilePath) {
  if (!fs.existsSync(commandFilePath)) {
    throw new Error(`command file not found: ${commandFilePath}`);
  }
  return JSON.parse(fs.readFileSync(commandFilePath, 'utf8'));
}

function executeCommand(cmd) {
  if (cmd.action !== 'npm_script') {
    return { pass: false, status: 1, reason: `unsupported action: ${cmd.action}` };
  }

  const script = String(cmd.value || '').trim();
  if (!ALLOWED_NPM_SCRIPTS.has(script)) {
    return { pass: false, status: 1, reason: `script not in allow-list: ${script}` };
  }

  const result = runCommand('npm', ['run', script]);
  return {
    pass: result.pass,
    status: result.status,
    stdout: result.stdout,
    stderr: result.stderr,
    reason: result.pass ? '' : 'npm script failed'
  };
}

function runPostValidation() {
  const py = pythonCmd();
  const elementary = runCommand(py, ['tools/validate_all_elementary_banks.py']);
  if (!elementary.pass) {
    return {
      pass: false,
      stage: 'validate_all_elementary_banks',
      status: elementary.status,
      reason: elementary.stderr || 'elementary bank validation failed',
    };
  }

  const verifyAll = runCommand('npm', ['run', 'verify:all']);
  if (!verifyAll.pass) {
    return {
      pass: false,
      stage: 'verify_all',
      status: verifyAll.status,
      reason: verifyAll.stderr || 'verify_all failed',
    };
  }

  return { pass: true, stage: 'validated', status: 0, reason: '' };
}

function autoCommitForCommand(commandId) {
  const statusRes = runCommand('git', ['status', '--porcelain']);
  const dirty = Boolean(statusRes.stdout && statusRes.stdout.trim());
  if (!dirty) {
    return { pass: true, status: 0, committed: false, pushed: false, commit_hash: null, reason: 'no changes' };
  }

  const addRes = runCommand('git', ['add', '-A']);
  if (!addRes.pass) {
    return { pass: false, status: addRes.status, committed: false, pushed: false, commit_hash: null, reason: addRes.stderr || 'git add failed' };
  }

  const commitMsg = `automation: execute command ${commandId} with verified checks`;
  let commitRes = runCommand('git', ['commit', '-m', commitMsg]);
  if (!commitRes.pass) {
    runCommand('git', ['add', '-A']);
    commitRes = runCommand('git', ['commit', '-m', commitMsg]);
  }
  if (!commitRes.pass) {
    return { pass: false, status: commitRes.status, committed: false, pushed: false, commit_hash: null, reason: commitRes.stderr || 'git commit failed' };
  }

  const hashRes = runCommand('git', ['rev-parse', '--short', 'HEAD']);
  const commitHash = hashRes.pass ? (hashRes.stdout || '').trim() : null;

  const pushRes = runCommand('git', ['push', 'origin', 'main']);
  if (!pushRes.pass) {
    return {
      pass: false,
      status: pushRes.status,
      committed: true,
      pushed: false,
      commit_hash: commitHash,
      reason: pushRes.stderr || 'git push failed'
    };
  }

  return { pass: true, status: 0, committed: true, pushed: true, commit_hash: commitHash, reason: '' };
}

async function runOnce(commandFilePath) {
  const now = new Date().toISOString();
  const state = readState();
  const executed = new Set(state.executed_ids || []);

  const pullRes = runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
  const pullOk = pullRes.pass;

  const payload = readCommandFile(commandFilePath);
  const commands = normalizeCommands(payload);
  const pending = commands.filter((c) => c.enabled && !executed.has(c.id));

  for (const cmd of pending) {
    const startedAt = new Date().toISOString();
    const result = executeCommand(cmd);
    let validation = { pass: false, stage: 'not-run', status: 1, reason: '' };
    let commitResult = { pass: false, status: 1, committed: false, pushed: false, commit_hash: null, reason: '' };

    if (result.pass) {
      validation = runPostValidation();
      if (validation.pass) {
        commitResult = autoCommitForCommand(cmd.id);
      }
    }

    const finalPass = result.pass && validation.pass && commitResult.pass;
    const endedAt = new Date().toISOString();

    const logEntry = {
      id: cmd.id,
      action: cmd.action,
      value: cmd.value,
      started_at: startedAt,
      ended_at: endedAt,
      pass: finalPass,
      status: finalPass ? 0 : (commitResult.status || validation.status || result.status),
      reason: finalPass ? '' : (commitResult.reason || validation.reason || result.reason || ''),
      note: cmd.note || '',
      command_result: { pass: result.pass, status: result.status },
      validation_result: validation,
      commit_result: commitResult
    };

    appendRunLog(logEntry);
    writeLatestStatus(logEntry);

    if (finalPass) {
      executed.add(cmd.id);
    }
  }

  const nextState = {
    last_checked_at: now,
    command_file: commandFilePath,
    git_pull_ok: pullOk,
    executed_ids: Array.from(executed)
  };
  writeState(nextState);

  writeLatestStatus({
    kind: 'poll-summary',
    checked_at: now,
    command_file: commandFilePath,
    git_pull_ok: pullOk,
    total_commands: commands.length,
    pending_executed: pending.length,
    executed_ids_count: nextState.executed_ids.length
  });

  console.log(JSON.stringify({
    checked_at: now,
    command_file: commandFilePath,
    git_pull_ok: pullOk,
    total_commands: commands.length,
    pending_executed: pending.length,
    executed_ids_count: nextState.executed_ids.length
  }, null, 2));
}

async function main() {
  const commandFilePath = argValue('--command-file', COMMAND_FILE_DEFAULT);
  const intervalMin = Number(argValue('--interval-min', '5'));
  const once = hasFlag('--once') || !hasFlag('--watch');

  if (once) {
    await runOnce(commandFilePath);
    return;
  }

  while (true) {
    try {
      await runOnce(commandFilePath);
    } catch (err) {
      appendRunLog({
        id: 'poll-error',
        started_at: new Date().toISOString(),
        ended_at: new Date().toISOString(),
        pass: false,
        status: 1,
        reason: String(err?.message || err)
      });
      console.error(err);
    }

    const ms = Math.max(1, intervalMin) * 60 * 1000;
    console.log(`sleep ${intervalMin} minutes before next command poll...`);
    await sleep(ms);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
