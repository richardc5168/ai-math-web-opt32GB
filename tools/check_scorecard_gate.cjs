const fs = require('fs');
const path = require('path');

const scorePath = path.join(process.cwd(), 'artifacts', 'scorecard.json');
const s = JSON.parse(fs.readFileSync(scorePath, 'utf8'));

const checks = {
  testsPass: s.tests.pass === true,
  axeCritical: s.axe.critical === 0,
  lighthouseAccessibility: s.lighthouse.accessibility >= 90,
  lighthousePerformance: s.lighthouse.performance >= 85,
  hintRubric: s.hint_rubric.avg >= 7.0,
  golden: s.golden.correct_rate >= 1.0,
  e2eFlakyRate: Number(s.e2e?.flaky_rate ?? 1) <= 0.02,
};

const ok = Object.values(checks).every(Boolean);
console.log(JSON.stringify({ ok, checks }, null, 2));
if (!ok) process.exit(1);
