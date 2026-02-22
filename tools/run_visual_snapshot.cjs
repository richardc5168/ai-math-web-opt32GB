const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { ensureArtifactsDir, writeJson } = require('./_runner.cjs');

async function run() {
  const { chromium } = require('@playwright/test');
  const pagePath = path.join(process.cwd(), 'docs', 'interactive-g5-life-pack2plus-empire', 'index.html');
  const url = `file:///${pagePath.replace(/\\/g, '/')}`;

  const artifacts = ensureArtifactsDir();
  const visualDir = path.join(artifacts, 'visual');
  fs.mkdirSync(visualDir, { recursive: true });

  const screenshotPath = path.join(visualDir, 'latest.png');
  const baselineHashPath = path.join(process.cwd(), 'golden', 'visual_baseline.sha256');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(url);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await browser.close();

  const data = fs.readFileSync(screenshotPath);
  const hash = crypto.createHash('sha256').update(data).digest('hex');

  const strict = process.env.VISUAL_STRICT === '1';
  let pass = true;
  let baselineCreated = false;
  let driftDetected = false;
  if (!fs.existsSync(baselineHashPath)) {
    fs.mkdirSync(path.dirname(baselineHashPath), { recursive: true });
    fs.writeFileSync(baselineHashPath, `${hash}\n`, 'utf8');
    baselineCreated = true;
  } else {
    const baseline = fs.readFileSync(baselineHashPath, 'utf8').trim();
    driftDetected = baseline !== hash;
    pass = strict ? !driftDetected : true;
  }

  const out = { pass, hash, baselineCreated, strict, driftDetected };
  writeJson('visual_results.json', out);
  if (!pass) process.exit(1);
  console.log('visual snapshot checks passed');
}

run().catch((err) => {
  writeJson('visual_results.json', { pass: false, error: String(err) });
  process.exit(1);
});
