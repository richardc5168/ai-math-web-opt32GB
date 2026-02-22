const fs = require('fs');
const path = require('path');
const { writeJson } = require('./_runner.cjs');

async function run() {
  const { chromium } = require('@playwright/test');
  const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
  const pagePath = path.join(process.cwd(), 'docs', 'interactive-g5-life-pack2plus-empire', 'index.html');
  const url = `file:///${pagePath.replace(/\\/g, '/')}`;

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url);
  await page.addScriptTag({ content: axeSource });
  const results = await page.evaluate(async () => await axe.run(document, {
    runOnly: {
      type: 'tag',
      values: ['wcag2a', 'wcag2aa'],
    },
  }));
  await browser.close();

  const allowlist = new Set(['select-name']);
  const ignored = results.violations.filter((v) => allowlist.has(v.id));
  const effectiveViolations = results.violations.filter((v) => !allowlist.has(v.id));

  const critical = effectiveViolations.filter((v) => v.impact === 'critical').length;
  const serious = effectiveViolations.filter((v) => v.impact === 'serious').length;
  const out = {
    pass: critical === 0,
    critical,
    serious,
    ignored: ignored.map((v) => ({ id: v.id, impact: v.impact, help: v.help })),
    violations: effectiveViolations.map((v) => ({ id: v.id, impact: v.impact, help: v.help })),
  };
  writeJson('axe_results.json', out);
  if (!out.pass) process.exit(1);
  console.log('axe checks passed');
}

run().catch((err) => {
  writeJson('axe_results.json', { pass: false, critical: 999, serious: 999, error: String(err) });
  process.exit(1);
});
