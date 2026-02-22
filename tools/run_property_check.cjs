const { pythonCmd, runCommand, writeJson } = require('./_runner.cjs');

const py = pythonCmd();
const run = runCommand(py, ['-m', 'pytest', 'tests/property', '-q']);
const result = { pass: run.pass, run };
writeJson('property_results.json', result);
if (!result.pass) process.exit(1);
console.log('property checks passed');
