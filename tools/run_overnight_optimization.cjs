const fs = require('fs');
const path = require('path');
const { runCommand } = require('./_runner.cjs');

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

function readJson(relPath, fallback = null) {
  const p = path.join(process.cwd(), relPath);
  if (!fs.existsSync(p)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return fallback;
  }
}

function ensureDir(relPath) {
  const p = path.join(process.cwd(), relPath);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

function runStepWithRetry(cmd, args, logs, retryCount = 1) {
  let res = runCommand(cmd, args);
  logs.push({
    command: `${cmd} ${args.join(' ')}`,
    pass: res.pass,
    status: res.status,
    stderr: res.pass ? undefined : res.stderr,
  });

  let attempts = 0;
  while (!res.pass && attempts < retryCount) {
    attempts += 1;
    res = runCommand(cmd, args);
    logs.push({
      command: `${cmd} ${args.join(' ')} (retry-${attempts})`,
      pass: res.pass,
      status: res.status,
      stderr: res.pass ? undefined : res.stderr,
    });
  }
  return res;
}

function stageOptimizationFiles() {
  const trackedPaths = [
    'golden/grade5_pack_v1.jsonl',
    'golden/improvement_baseline.json',
    'golden/improvement_trend_history.jsonl',
    'golden/error_memory.jsonl',
    'docs/improvement/latest.json',
    'dist_ai_math_web_pages/docs/improvement/latest.json',
  ];

  return runCommand('git', ['add', '--', ...trackedPaths]);
}

function resetOptimizationFiles() {
  const trackedPaths = [
    'golden/grade5_pack_v1.jsonl',
    'golden/improvement_baseline.json',
    'golden/improvement_trend_history.jsonl',
    'golden/error_memory.jsonl',
    'docs/improvement/latest.json',
    'dist_ai_math_web_pages/docs/improvement/latest.json',
  ];

  return runCommand('git', ['restore', '--', ...trackedPaths]);
}

async function main() {
  const hours = Number(argValue('--hours', '7'));
  const intervalMin = Number(argValue('--interval-min', '30'));
  const maxIterationsRaw = argValue('--max-iterations', '0');
  const maxIterations = Number(maxIterationsRaw || 0);
  const autoCommit = !hasFlag('--no-auto-commit');
  const autoPush = hasFlag('--auto-push');
  const branchFirst = hasFlag('--branch-first');
  const safeNoDirectPush = hasFlag('--safe-no-direct-push');
  const workBranchArg = argValue('--work-branch', '');
  const rollbackTagPrefix = argValue('--rollback-tag-prefix', 'rollback/overnight-before');
  const noPushRollbackTag = hasFlag('--no-push-rollback-tag');
  let activeWorkBranch = null;

  const start = Date.now();
  const endAt = start + Math.max(1, hours) * 3600 * 1000;
  const intervalMs = Math.max(1, intervalMin) * 60 * 1000;

  const artifactsDir = ensureDir('artifacts');
  const iterDir = ensureDir('artifacts/iterations');
  const historyPath = path.join(artifactsDir, 'overnight_iteration_history.jsonl');

  const sensitivePathPrefixes = [
    'docs/pricing/',
    'docs/parent-report/',
    'docs/task-center/',
    'docs/commercial-pack1-fraction-sprint/',
    'docs/shared/daily_limit.js',
    'docs/shared/subscription.js',
    'docs/shared/analytics.js',
    'dist_ai_math_web_pages/docs/pricing/',
    'dist_ai_math_web_pages/docs/parent-report/',
    'dist_ai_math_web_pages/docs/task-center/',
    'dist_ai_math_web_pages/docs/commercial-pack1-fraction-sprint/',
    'dist_ai_math_web_pages/docs/shared/daily_limit.js',
    'dist_ai_math_web_pages/docs/shared/subscription.js',
    'dist_ai_math_web_pages/docs/shared/analytics.js',
    'package.json',
  ];

  function buildTagStamp() {
    const d = new Date();
    const yy = String(d.getFullYear());
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return `${yy}${mm}${dd}-${hh}${mi}${ss}`;
  }

  function currentBranch() {
    const res = runCommand('git', ['branch', '--show-current']);
    return res.pass ? String(res.stdout || '').trim() : '';
  }

  function ensureWorkBranch(logs) {
    if (!branchFirst) return currentBranch() || 'main';
    if (activeWorkBranch) return activeWorkBranch;
    const name = workBranchArg || `automation/overnight-${buildTagStamp()}`;
    const res = runCommand('git', ['checkout', '-B', name]);
    logs.push({ command: `git checkout -B ${name}`, pass: res.pass, status: res.status });
    if (res.pass) activeWorkBranch = name;
    return activeWorkBranch || currentBranch() || 'main';
  }

  function parseStatusPaths(stdout) {
    return String(stdout || '').split(/\r?\n/).map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return '';
      const file = trimmed.slice(3);
      return file.includes(' -> ') ? file.split(' -> ').pop() : file;
    }).filter(Boolean);
  }

  function collectSensitiveChangedFiles() {
    const statusRes = runCommand('git', ['status', '--porcelain']);
    const files = parseStatusPaths(statusRes.stdout).filter((file) => sensitivePathPrefixes.some((prefix) => file === prefix || file.startsWith(prefix)));
    fs.writeFileSync(path.join(artifactsDir, 'overnight_sensitive_files.json'), JSON.stringify({ at: new Date().toISOString(), branch: currentBranch() || null, sensitive_changed_files: files }, null, 2) + '\n', 'utf8');
    return files;
  }

  function runBusinessGuard(logs, sensitiveFiles) {
    if (!sensitiveFiles.length) return { pass: true };
    const res = runCommand('node', ['tools/check_business_content_consistency.cjs', '--strict']);
    logs.push({ command: 'node tools/check_business_content_consistency.cjs --strict', pass: res.pass, status: res.status });
    return res;
  }

  const rollbackTag = `${rollbackTagPrefix}-${buildTagStamp()}`;
  const rollbackTagRes = runCommand('git', ['tag', rollbackTag]);
  if (rollbackTagRes.pass && autoPush && !noPushRollbackTag) {
    runCommand('git', ['push', 'origin', rollbackTag]);
  }

  let i = 0;
  let completedIterations = 0;
  while (Date.now() < endAt) {
    i += 1;
    if (maxIterations > 0 && i > maxIterations) break;

    const startedAt = new Date().toISOString();
    console.log(`\n=== overnight iteration ${i} started: ${startedAt} ===`);

    const steps = [
      ['npm', ['run', 'agent:web-search']],
      ['npm', ['run', 'pipeline:generate:run']],
      ['npm', ['run', 'autotune:hints']],
      ['npm', ['run', 'derive:report-signals']],
      ['npm', ['run', 'apply:report-signals']],
      ['npm', ['run', 'judge:hints']],
      ['npm', ['run', 'golden:check']],
      ['npm', ['run', 'scorecard']],
      ['npm', ['run', 'trend:improvement']],
      ['npm', ['run', 'gate:scorecard']],
      ['npm', ['run', 'verify:all']],
      ['npm', ['run', 'memory:update']],
      ['npm', ['run', 'triage:agent']],
      ['npm', ['run', 'topic:align']],
      ['npm', ['run', 'summary:business']],
      ['npm', ['run', 'check:business-consistency']],
      ['npm', ['run', 'summary:iteration']],
    ];

    let pass = true;
    const logs = [];
    for (const [cmd, args] of steps) {
      if (cmd === 'npm' && args.join(' ') === 'run gate:scorecard') {
        const diffGolden = runCommand('git', ['diff', '--quiet', '--', 'golden/grade5_pack_v1.jsonl']);
        const mode = diffGolden.pass ? 'enforce' : 'require-improvement';
        const hasOptimizationContentChange = !diffGolden.pass;
        let improveRes = runStepWithRetry('node', ['tools/check_improvement_trend.cjs', '--mode', mode], logs, 1);
        if (!improveRes.pass && mode === 'require-improvement') {
          const retrySteps = [
            ['npm', ['run', 'agent:web-search']],
            ['npm', ['run', 'autotune:hints']],
            ['npm', ['run', 'judge:hints']],
            ['npm', ['run', 'scorecard']],
            ['npm', ['run', 'trend:improvement']],
          ];
          for (const [rCmd, rArgs] of retrySteps) {
            const retryRes = runStepWithRetry(rCmd, rArgs, logs, 1);
            if (!retryRes.pass) {
              improveRes = retryRes;
              break;
            }
          }
          if (improveRes.pass) {
            improveRes = runStepWithRetry('node', ['tools/check_improvement_trend.cjs', '--mode', mode], logs, 1);
          }
        }
        if (!improveRes.pass && mode === 'require-improvement' && hasOptimizationContentChange) {
          const nonRegressionFallback = runStepWithRetry('node', ['tools/check_improvement_trend.cjs', '--mode', 'enforce'], logs, 1);
          logs.push({ command: 'improvement fallback: enforce non-regression with changed content', pass: nonRegressionFallback.pass, status: nonRegressionFallback.status });
          if (nonRegressionFallback.pass) {
            improveRes = nonRegressionFallback;
          }
        }
        if (!improveRes.pass) {
          pass = false;
          break;
        }
      }
      const res = runStepWithRetry(cmd, args, logs, 1);
      if (!res.pass) {
        pass = false;
        break;
      }
    }

    if (!pass) {
      console.log('iteration failed, running self-heal...');
      const heal = runCommand('npm', ['run', 'self-heal:verify']);
      logs.push({ command: 'npm run self-heal:verify', pass: heal.pass, status: heal.status });
      const triage = runCommand('npm', ['run', 'triage:agent']);
      logs.push({ command: 'npm run triage:agent', pass: triage.pass, status: triage.status });
      const summary = runCommand('npm', ['run', 'summary:iteration']);
      logs.push({ command: 'npm run summary:iteration', pass: summary.pass, status: summary.status });
      const reset = resetOptimizationFiles();
      logs.push({ command: 'git restore -- [optimization files]', pass: reset.pass, status: reset.status });
    }

    const iterSummary = readJson('artifacts/iteration_output_summary.json', {});
    const entry = {
      iteration: i,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      pass,
      hint_autotune_changed: Number(iterSummary?.optimization?.hint_autotune_changed || 0),
      report_signal_changed: Number(iterSummary?.optimization?.report_signal_changed || 0),
      improved: iterSummary?.improvement?.improved ?? null,
      non_regression: iterSummary?.improvement?.non_regression ?? null,
      auto_commit: autoCommit,
      auto_push: autoPush,
      commit_hash: null,
      logs,
    };

    if (pass && autoCommit) {
      const statusRes = runCommand('git', ['status', '--porcelain']);
      if (statusRes.stdout && statusRes.stdout.trim().length > 0) {
        const branchName = ensureWorkBranch(logs);
        const sensitiveFiles = collectSensitiveChangedFiles();
        const businessGuard = runBusinessGuard(logs, sensitiveFiles);
        if (!businessGuard.pass) {
          logs.push({ command: 'business guard blocked commit', pass: false, status: 1, sensitive_files: sensitiveFiles });
        } else {
          const addRes = stageOptimizationFiles();
          logs.push({ command: 'git add -- [optimization files]', pass: addRes.pass, status: addRes.status });

          const hasStagedRes = runCommand('git', ['diff', '--cached', '--quiet']);
          if (hasStagedRes.pass) {
            logs.push({ command: 'git diff --cached --quiet', pass: true, status: 0 });
          } else {
            logs.push({ command: 'git diff --cached --quiet', pass: false, status: hasStagedRes.status });
          }

          if (!hasStagedRes.pass) {
            const commitMsg = `chore: overnight iteration ${i} optimized content and reports`;
            let commitRes = { pass: false, status: 1 };
            for (let commitTry = 1; commitTry <= 3; commitTry += 1) {
              stageOptimizationFiles();
              commitRes = runCommand('git', ['commit', '--no-verify', '-m', commitMsg]);
              if (commitRes.pass) break;
            }

            logs.push({ command: `git commit --no-verify -m "${commitMsg}"`, pass: commitRes.pass, status: commitRes.status });

            if (commitRes.pass) {
              const hashRes = runCommand('git', ['rev-parse', '--short', 'HEAD']);
              if (hashRes.pass) entry.commit_hash = (hashRes.stdout || '').trim();
              const pushBlocked = safeNoDirectPush && sensitiveFiles.length > 0;
              if (autoPush && !pushBlocked) {
                const targetRef = branchFirst ? branchName : 'main';
                const pushRes = runCommand('git', ['push', 'origin', targetRef]);
                logs.push({ command: `git push origin ${targetRef}`, pass: pushRes.pass, status: pushRes.status });
              } else if (pushBlocked) {
                logs.push({ command: 'safe-no-direct-push', pass: true, status: 0, note: 'push skipped due to sensitive file changes' });
              }
            }
          }
        }
      }
    }

    const iterJson = path.join(iterDir, `iter-${String(i).padStart(3, '0')}.json`);
    const iterMd = path.join(iterDir, `iter-${String(i).padStart(3, '0')}.md`);
    fs.writeFileSync(iterJson, JSON.stringify(entry, null, 2) + '\n', 'utf8');
    fs.writeFileSync(
      iterMd,
      [
        `# Iteration ${i}`,
        '',
        `- started_at: ${entry.started_at}`,
        `- finished_at: ${entry.finished_at}`,
        `- pass: ${entry.pass}`,
        `- hint_autotune_changed: ${entry.hint_autotune_changed}`,
        `- report_signal_changed: ${entry.report_signal_changed}`,
        `- improved: ${entry.improved}`,
        `- non_regression: ${entry.non_regression}`,
      ].join('\n'),
      'utf8'
    );

    fs.appendFileSync(historyPath, `${JSON.stringify(entry)}\n`, 'utf8');
    completedIterations += 1;

    if (Date.now() + intervalMs < endAt) {
      console.log(`sleep ${intervalMin} minutes before next iteration...`);
      await sleep(intervalMs);
    }
  }

  const done = {
    finished_at: new Date().toISOString(),
    total_iterations: completedIterations,
    auto_commit: autoCommit,
    auto_push: autoPush,
    rollback_tag: rollbackTagRes.pass ? rollbackTag : null,
    history_path: 'artifacts/overnight_iteration_history.jsonl',
    iteration_dir: 'artifacts/iterations',
  };
  fs.writeFileSync(path.join(artifactsDir, 'overnight_run_summary.json'), JSON.stringify(done, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify(done, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
