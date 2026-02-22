const { runCommand } = require('./_runner.cjs');

const steps = [
  'lint',
  'test:unit',
  'test:contract',
  'test:property',
  'test:e2e',
  'test:axe',
  'test:lighthouse',
  'test:visual',
  'judge:hints',
  'golden:check',
  'scorecard',
  'gate:scorecard',
];

for (const step of steps) {
  console.log(`\n==> ${step}`);
  const res = runCommand('npm', ['run', step]);
  if (res.stdout) console.log(res.stdout);
  if (res.stderr) console.error(res.stderr);
  if (!res.pass) {
    console.error(`verify:all failed at step ${step}`);
    process.exit(1);
  }
}

console.log('\nverify:all passed');
