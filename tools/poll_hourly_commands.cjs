const fs = require('fs');
const path = require('path');
const https = require('https');
const { runCommand, pythonCmd } = require('./_runner.cjs');

const COMMAND_FILE_DEFAULT = path.join(process.cwd(), 'ops', 'hourly_commands.json');
const STATE_PATH_DEFAULT = path.join(process.cwd(), 'artifacts', 'hourly_command_state.json');
const RUN_LOG_PATH_DEFAULT = path.join(process.cwd(), 'artifacts', 'hourly_command_runs.jsonl');
const LATEST_STATUS_PATH_DEFAULT = path.join(process.cwd(), 'artifacts', 'hourly_command_latest.json');

const ALLOWED_NPM_SCRIPTS = new Set([
  'verify:all',
  'topic:align',
  'summary:iteration',
  'summary:hints',
  'summary:kpi',
  'autotune:hints',
  'triage:agent',
  'agent:web-search',
  'memory:update',
  'judge:hints',
  'scorecard',
  'trend:improvement',
  'gate:scorecard',
  'optimize:g5g6:web:5h',
  'overnight:optimize',
  'idle:web:fraction-decimal:expand',
  'fraction-decimal:web:ingest',
  'fraction-decimal:web:build',
  'fraction-decimal:web:validate',
  'test:fraction-decimal:web',
  'external:web:ingest',
  'external:web:build',
  'external:web:validate',
  'test:external:fraction',
  'verify:kind-coverage',
  'status:mail',
  'pipeline:agent-loop',
  'pipeline:agent-loop:run',
  'pipeline:generate',
  'pipeline:generate:run',
  'pipeline:coverage',
  'pipeline:solver:test',
  'autonomous:12h',
  'autonomous:8h',
  'autonomous:dry'
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

function toRawGithubUrl(urlLike) {
  const s = String(urlLike || '').trim();
  if (!s.includes('github.com')) return s;
  const marker = '/blob/';
  if (!s.includes(marker)) return s;
  return s.replace('https://github.com/', 'https://raw.githubusercontent.com/').replace(marker, '/');
}

function fetchText(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'User-Agent': 'ai-math-web/hourly-command-poller',
        'Accept': 'application/json,text/plain,*/*'
      },
      timeout: 15000,
    }, (res) => {
      if (!res || typeof res.statusCode !== 'number') {
        reject(new Error(`invalid response: ${url}`));
        return;
      }
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers && res.headers.location) {
        const redirected = String(res.headers.location);
        fetchText(redirected).then(resolve).catch(reject);
        return;
      }
      if (res.statusCode < 200 || res.statusCode >= 300) {
        reject(new Error(`http ${res.statusCode} from ${url}`));
        return;
      }
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => resolve(data));
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy(new Error(`timeout fetching ${url}`));
    });
  });
}

function parseJsonWithObjectFallback(content, sourceLabel) {
  try {
    return JSON.parse(content);
  } catch {
    const first = content.indexOf('{');
    if (first < 0) {
      throw new Error(`invalid json in ${sourceLabel}: no object start`);
    }
    let depth = 0;
    let end = -1;
    for (let i = first; i < content.length; i += 1) {
      const ch = content[i];
      if (ch === '{') depth += 1;
      if (ch === '}') {
        depth -= 1;
        if (depth === 0) {
          end = i;
          break;
        }
      }
    }
    if (end < 0) {
      throw new Error(`invalid json in ${sourceLabel}: no balanced object end`);
    }
    const slice = content.slice(first, end + 1);
    return JSON.parse(slice);
  }
}

function ensureArtifacts() {
  const p = path.join(process.cwd(), 'artifacts');
  fs.mkdirSync(p, { recursive: true });
}

function readState(statePath) {
  if (!fs.existsSync(statePath)) return { executed_ids: [] };
  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf8'));
  } catch {
    return { executed_ids: [] };
  }
}

function writeState(statePath, state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
}

function appendRunLog(runLogPath, entry) {
  fs.mkdirSync(path.dirname(runLogPath), { recursive: true });
  fs.appendFileSync(runLogPath, `${JSON.stringify(entry)}\n`, 'utf8');
}

function writeLatestStatus(latestStatusPath, status) {
  fs.mkdirSync(path.dirname(latestStatusPath), { recursive: true });
  fs.writeFileSync(latestStatusPath, JSON.stringify(status, null, 2) + '\n', 'utf8');
}

function normalizeCommands(payload) {
  if (!payload || !Array.isArray(payload.commands)) return [];
  return payload.commands.filter((c) => c && typeof c.id === 'string');
}

function parseIsoMs(v) {
  const t = Date.parse(String(v || ''));
  return Number.isFinite(t) ? t : 0;
}

function shouldRunCommand(cmd, executed, lastRunAtMap, nowMs) {
  if (!cmd || !cmd.enabled) return false;

  const cooldownMinutes = Number(cmd.cooldown_minutes || 0);
  if (Number.isFinite(cooldownMinutes) && cooldownMinutes > 0) {
    const lastAt = parseIsoMs(lastRunAtMap[String(cmd.id || '')]);
    if (!lastAt) return true;
    const elapsedMin = (nowMs - lastAt) / 60000;
    return elapsedMin >= cooldownMinutes;
  }

  return !executed.has(cmd.id);
}

async function readCommandSource(commandFilePath, commandUrl) {
  if (commandUrl) {
    const rawUrl = toRawGithubUrl(commandUrl);
    try {
      const text = await fetchText(rawUrl);
      return parseJsonWithObjectFallback(text, rawUrl);
    } catch (err) {
      if (fs.existsSync(commandFilePath)) {
        const localText = fs.readFileSync(commandFilePath, 'utf8');
        return parseJsonWithObjectFallback(localText, commandFilePath);
      }
      throw err;
    }
  }
  if (!fs.existsSync(commandFilePath)) {
    throw new Error(`command file not found: ${commandFilePath}`);
  }
  const text = fs.readFileSync(commandFilePath, 'utf8');
  return parseJsonWithObjectFallback(text, commandFilePath);
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
  if (script === 'status:mail' && !result.pass) {
    return {
      pass: true,
      status: 0,
      stdout: result.stdout,
      stderr: result.stderr,
      reason: 'status mail skipped'
    };
  }
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
  let commitRes = runCommand('git', ['commit', '--no-verify', '-m', commitMsg]);
  if (!commitRes.pass) {
    runCommand('git', ['add', '-A']);
    commitRes = runCommand('git', ['commit', '--no-verify', '-m', commitMsg]);
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

async function runOnce(commandFilePath, commandUrl, statePath, runLogPath, latestStatusPath, persistExecutedOnly) {
  const now = new Date().toISOString();
  const nowMs = Date.now();
  const state = readState(statePath);
  const executed = new Set(state.executed_ids || []);
  const lastRunAtMap = (state && typeof state.command_last_run_at === 'object' && state.command_last_run_at)
    ? { ...state.command_last_run_at }
    : {};

  const pullRes = runCommand('git', ['pull', '--ff-only', 'origin', 'main']);
  const pullOk = pullRes.pass;

  const payload = await readCommandSource(commandFilePath, commandUrl);
  const commands = normalizeCommands(payload);
  const pending = commands.filter((c) => shouldRunCommand(c, executed, lastRunAtMap, nowMs));

  for (const cmd of pending) {
    const startedAt = new Date().toISOString();
    lastRunAtMap[String(cmd.id)] = startedAt;
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

    appendRunLog(runLogPath, logEntry);
    writeLatestStatus(latestStatusPath, logEntry);

    if (finalPass) {
      executed.add(cmd.id);
    }
  }

  const nextState = persistExecutedOnly
    ? {
        executed_ids: Array.from(executed),
        command_last_run_at: lastRunAtMap,
      }
    : {
        last_checked_at: now,
        command_file: commandFilePath,
        command_url: commandUrl || null,
        git_pull_ok: pullOk,
        executed_ids: Array.from(executed),
        command_last_run_at: lastRunAtMap,
      };
  writeState(statePath, nextState);

  writeLatestStatus(latestStatusPath, {
    kind: 'poll-summary',
    checked_at: now,
    command_file: commandFilePath,
    command_url: commandUrl || null,
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
  const commandUrl = argValue('--command-url', '');
  const statePath = argValue('--state-file', STATE_PATH_DEFAULT);
  const runLogPath = argValue('--run-log-file', RUN_LOG_PATH_DEFAULT);
  const latestStatusPath = argValue('--latest-status-file', LATEST_STATUS_PATH_DEFAULT);
  const persistExecutedOnly = hasFlag('--persist-executed-only');
  const intervalMin = Number(argValue('--interval-min', '5'));
  const maxHours = Number(argValue('--max-hours', '0'));
  const once = hasFlag('--once') || !hasFlag('--watch');
  const startedAt = Date.now();

  if (once) {
    await runOnce(commandFilePath, commandUrl, statePath, runLogPath, latestStatusPath, persistExecutedOnly);
    return;
  }

  while (true) {
    try {
      await runOnce(commandFilePath, commandUrl, statePath, runLogPath, latestStatusPath, persistExecutedOnly);
    } catch (err) {
      appendRunLog(runLogPath, {
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
    if (maxHours > 0 && (Date.now() - startedAt) >= maxHours * 3600 * 1000) {
      console.log(`max-hours reached (${maxHours}), exiting watcher.`);
      return;
    }
    console.log(`sleep ${intervalMin} minutes before next command poll...`);
    await sleep(ms);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
