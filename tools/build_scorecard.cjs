const fs = require('fs');
const path = require('path');
const Ajv = require('ajv');
const { writeJson } = require('./_runner.cjs');

function readJson(name, fallback = {}) {
  const p = path.join(process.cwd(), 'artifacts', name);
  if (!fs.existsSync(p)) return fallback;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const lint = readJson('lint_results.json');
const unit = readJson('unit_results.json');
const contract = readJson('contract_results.json');
const property = readJson('property_results.json');
const e2e = readJson('e2e_results.json');
const axe = readJson('axe_results.json');
const lighthouse = readJson('lighthouse_results.json');
const visual = readJson('visual_results.json');
const hintJudge = readJson('hint_judge.json', { summary: { avg_score: 0 } });
const golden = readJson('golden_results.json', { correct_rate: 0 });

const testsPass = [lint, unit, contract, property, e2e, visual].every((x) => x.pass === true);

const scorecard = {
  version: 'scorecard.v1',
  timestamp: new Date().toISOString(),
  tests: {
    pass: testsPass,
    lint: !!lint.pass,
    unit: !!unit.pass,
    contract: !!contract.pass,
    property: !!property.pass,
    e2e: !!e2e.pass,
    visual: !!visual.pass,
  },
  lighthouse: {
    performance: Number(lighthouse.performance || 0),
    accessibility: Number(lighthouse.accessibility || 0),
  },
  axe: {
    critical: Number(axe.critical || 0),
  },
  hint_rubric: {
    avg: Number(hintJudge.summary?.avg_score || 0),
  },
  golden: {
    correct_rate: Number(golden.correct_rate || 0),
  },
};

const schemaPath = path.join(process.cwd(), 'schemas', 'scorecard.schema.json');
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(schema);
const ok = validate(scorecard);
if (!ok) {
  console.error(validate.errors);
  process.exit(1);
}

const outArg = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : null;
const outName = outArg ? path.basename(outArg) : 'scorecard.json';
writeJson(outName, scorecard);
console.log('scorecard built');
