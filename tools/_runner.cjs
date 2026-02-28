const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function ensureArtifactsDir() {
  const dir = path.join(process.cwd(), 'artifacts');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function pythonCmd() {
  const candidates = [
    process.env.VERIFY_PYTHON,
    path.join(process.cwd(), '.venv', 'Scripts', 'python.exe'),
    path.join(process.cwd(), '.venv', 'bin', 'python'),
    'python',
  ].filter(Boolean);
  return candidates.find((p) => {
    if (p === 'python') return true;
    return fs.existsSync(p);
  }) || 'python';
}

function resolveCommand(command) {
  if (process.platform !== 'win32') return command;
  if (command === 'npm') return 'npm.cmd';
  if (command === 'npx') return 'npx.cmd';
  return command;
}

function runCommand(command, args, options = {}) {
  const execCommand = resolveCommand(command);
  const commandLine = [execCommand, ...args].join(' ');
  let proc = spawnSync(execCommand, args, {
    cwd: process.cwd(),
    encoding: 'utf-8',
    shell: options.shell ?? false,
    ...options,
  });

  if (process.platform === 'win32' && proc.error && options.shell === undefined) {
    proc = spawnSync(commandLine, {
      cwd: process.cwd(),
      encoding: 'utf-8',
      shell: true,
      ...options,
    });
  }

  return {
    command: [command, ...args].join(' '),
    status: proc.status ?? 1,
    stdout: (proc.stdout || '').trim(),
    stderr: (proc.stderr || '').trim(),
    error: proc.error ? String(proc.error.message || proc.error) : null,
    timedOut: Boolean(proc.error && proc.error.code === 'ETIMEDOUT'),
    pass: (proc.status ?? 1) === 0,
  };
}

function writeJson(name, data) {
  ensureArtifactsDir();
  const outPath = path.join(process.cwd(), 'artifacts', name);
  fs.writeFileSync(outPath, JSON.stringify(data, null, 2), 'utf-8');
  return outPath;
}

module.exports = {
  ensureArtifactsDir,
  pythonCmd,
  runCommand,
  writeJson,
};
