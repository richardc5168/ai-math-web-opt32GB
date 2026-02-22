const { pythonCmd, runCommand, writeJson } = require('./_runner.cjs');

const py = pythonCmd();
const pyCompile = runCommand(py, ['-m', 'compileall', '-q', 'scripts', 'tools', 'tests']);
const nodeCheck = runCommand('node', ['--check', 'tools/build_scorecard.cjs']);

const pass = pyCompile.pass && nodeCheck.pass;
const result = {
  pass,
  checks: {
    pyCompile,
    nodeCheck,
  },
};

writeJson('lint_results.json', result);
if (!pass) {
  console.error('lint check failed');
  process.exit(1);
}
console.log('lint check passed');
