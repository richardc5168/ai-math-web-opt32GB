const fs = require('fs');
const path = require('path');
const { writeJson } = require('./_runner.cjs');

function fileSizeKb(p) {
  if (!fs.existsSync(p)) return 0;
  return fs.statSync(p).size / 1024;
}

function linkedFiles(html) {
  const links = [];
  const re = /(src|href)=\"([^\"]+)\"/g;
  let m;
  while ((m = re.exec(html))) {
    const v = m[2];
    if (v.endsWith('.js') || v.endsWith('.css')) links.push(v);
  }
  return links;
}

const pageFile = path.join(process.cwd(), 'docs', 'interactive-g5-life-pack2plus-empire', 'index.html');
const html = fs.readFileSync(pageFile, 'utf8');
const refs = linkedFiles(html);

let totalKb = fileSizeKb(pageFile);
for (const ref of refs) {
  const p = path.join(path.dirname(pageFile), ref);
  totalKb += fileSizeKb(p);
}

const hasTitle = /<title>[^<]+<\/title>/i.test(html);
const hasLang = /<html[^>]*lang=\"[^\"]+\"/i.test(html);
const hasViewport = /name=\"viewport\"/i.test(html);
const imgWithoutAlt = (html.match(/<img(?![^>]*alt=)[^>]*>/gi) || []).length;

let accessibility = 100;
if (!hasTitle) accessibility -= 5;
if (!hasLang) accessibility -= 5;
if (!hasViewport) accessibility -= 3;
accessibility -= Math.min(20, imgWithoutAlt * 2);
accessibility = Math.max(0, accessibility);

let performance = 100;
if (totalKb > 3000) performance = 70;
else if (totalKb > 2000) performance = 80;
else if (totalKb > 1200) performance = 88;
else if (totalKb > 800) performance = 92;

const out = {
  pass: accessibility >= 90 && performance >= 85,
  engine: 'budget-lite',
  performance,
  accessibility,
  totalKb: Number(totalKb.toFixed(2)),
};

writeJson('lighthouse_results.json', out);
if (!out.pass) process.exit(1);
console.log('lighthouse-lite checks passed');
