const fs = require('fs');
const path = require('path');
const { runCommand } = require('./_runner.cjs');

function pythonCommand() {
  const candidates = [
    process.env.VERIFY_PYTHON,
    path.join(process.cwd(), '.venv', 'Scripts', 'python.exe'),
    path.join(process.cwd(), '.venv', 'bin', 'python'),
    'python',
  ].filter(Boolean);
  return candidates.find((v) => v === 'python' || fs.existsSync(v)) || 'python';
}

function readLines(text) {
  return (text || '').split(/\r?\n/).map((v) => v.trim()).filter(Boolean);
}

const py = pythonCommand();
const report = {
  generated_at: new Date().toISOString(),
  steps: [],
  changed_files: [],
  verify_after_fix: null,
  success: false,
};

const steps = [
  { name: 'canonical_json_write', cmd: 'node', args: ['tools/check_policy_json_canonical.cjs', '--write'] },
  { name: 'fix_elementary_banks', cmd: py, args: ['tools/fix_all_elementary_banks.py'] },
  { name: 'sync_docs_dist', cmd: py, args: ['scripts/sync_docs_dist.py'] },
  { name: 'auto_iterate_quality', cmd: 'node', args: ['tools/auto_iterate_quality.cjs', '--apply'] },
  { name: 'quality_nightly_gate', cmd: 'node', args: ['tools/check_quality_nightly_gate.cjs'] },
];

for (const s of steps) {
  const res = runCommand(s.cmd, s.args);
  report.steps.push({
    name: s.name,
    pass: res.pass,
    status: res.status,
    stdout_head: readLines(res.stdout).slice(0, 8),
    stderr_head: readLines(res.stderr).slice(0, 8),
  });
}

const diffRes = runCommand('git', ['diff', '--name-only']);
report.changed_files = readLines(diffRes.stdout);

const verifyRes = runCommand('npm', ['run', 'verify:all']);
report.verify_after_fix = {
  pass: verifyRes.pass,
  status: verifyRes.status,
  stdout_head: readLines(verifyRes.stdout).slice(0, 20),
  stderr_head: readLines(verifyRes.stderr).slice(0, 20),
};

const qualityRes = runCommand('node', ['tools/check_quality_nightly_gate.cjs']);
report.quality_gate_after_fix = {
  pass: qualityRes.pass,
  status: qualityRes.status,
  stdout_head: readLines(qualityRes.stdout).slice(0, 20),
  stderr_head: readLines(qualityRes.stderr).slice(0, 20),
};

report.success = report.verify_after_fix.pass && report.quality_gate_after_fix.pass;

const artifactsDir = path.join(process.cwd(), 'artifacts');
fs.mkdirSync(artifactsDir, { recursive: true });
fs.writeFileSync(path.join(artifactsDir, 'self_heal_report.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');

console.log(JSON.stringify({ success: report.success, changed_files: report.changed_files.length }, null, 2));
if (!report.success) process.exit(1);
