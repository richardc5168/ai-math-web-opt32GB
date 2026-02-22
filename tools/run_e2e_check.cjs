const { runCommand, writeJson } = require('./_runner.cjs');

const run = runCommand(
	'npx',
	['playwright', 'test', 'tests_js/exam-sprint-gate.spec.mjs', '--reporter=line,html'],
	{
		env: {
			...process.env,
			PLAYWRIGHT_HTML_REPORT: 'artifacts/playwright-report',
		},
	}
);
const result = { pass: run.pass, flaky_rate: run.pass ? 0 : 1, run };
writeJson('e2e_results.json', result);
if (!result.pass) process.exit(1);
console.log('e2e checks passed');
