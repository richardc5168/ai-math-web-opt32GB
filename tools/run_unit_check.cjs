const { pythonCmd, runCommand, writeJson } = require('./_runner.cjs');

const py = pythonCmd();
const tests = [
  'tests/test_fraction_word_g5_clarity.py',
  'tests/test_fraction_word_g5_bank_logic_scan.py',
  'tests/test_hints_next_api_ratio_reverse.py',
  'tests/test_fraction_word_g5_ratio_reverse_ui_smoke.py',
];

const run = runCommand(py, ['-m', 'pytest', ...tests, '-q']);
const result = { pass: run.pass, run, tests };
writeJson('unit_results.json', result);
if (!result.pass) process.exit(1);
console.log('unit checks passed');
