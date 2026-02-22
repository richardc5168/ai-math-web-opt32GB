const { runCommand, writeJson } = require('./_runner.cjs');

const run = runCommand('npx', ['playwright', 'test', 'tests_js/exam-sprint-gate.spec.mjs', '--reporter=line']);
const result = { pass: run.pass, run };
writeJson('e2e_results.json', result);
if (!result.pass) process.exit(1);
console.log('e2e checks passed');
