const fs = require('fs');
const path = require('path');
const { runCommand } = require('./_runner.cjs');

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
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

async function main() {
  const hours = Number(argValue('--hours', '7'));
  const intervalMin = Number(argValue('--interval-min', '30'));
  const maxIterationsRaw = argValue('--max-iterations', '0');
  const maxIterations = Number(maxIterationsRaw || 0);

  const start = Date.now();
  const endAt = start + Math.max(1, hours) * 3600 * 1000;
  const intervalMs = Math.max(1, intervalMin) * 60 * 1000;

  const artifactsDir = ensureDir('artifacts');
  const iterDir = ensureDir('artifacts/iterations');
  const historyPath = path.join(artifactsDir, 'overnight_iteration_history.jsonl');

  let i = 0;
  let completedIterations = 0;
  while (Date.now() < endAt) {
    i += 1;
    if (maxIterations > 0 && i > maxIterations) break;

    const startedAt = new Date().toISOString();
    console.log(`\n=== overnight iteration ${i} started: ${startedAt} ===`);

    const steps = [
      ['npm', ['run', 'autotune:hints']],
      ['npm', ['run', 'derive:report-signals']],
      ['npm', ['run', 'apply:report-signals']],
      ['npm', ['run', 'judge:hints']],
      ['npm', ['run', 'golden:check']],
      ['npm', ['run', 'scorecard']],
      ['npm', ['run', 'trend:improvement']],
      ['npm', ['run', 'check:improvement']],
      ['npm', ['run', 'gate:scorecard']],
      ['npm', ['run', 'verify:all']],
      ['npm', ['run', 'triage:agent']],
      ['npm', ['run', 'topic:align']],
      ['npm', ['run', 'summary:iteration']],
    ];

    let pass = true;
    const logs = [];
    for (const [cmd, args] of steps) {
      const res = runCommand(cmd, args);
      logs.push({ command: `${cmd} ${args.join(' ')}`, pass: res.pass, status: res.status });
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
      logs,
    };

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
