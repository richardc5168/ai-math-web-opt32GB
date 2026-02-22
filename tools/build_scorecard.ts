import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import Ajv from 'ajv';

function readJson(name: string, fallback: any = {}) {
  const p = join(process.cwd(), 'artifacts', name);
  if (!existsSync(p)) return fallback;
  return JSON.parse(readFileSync(p, 'utf8'));
}

const lint = readJson('lint_results.json');
const unit = readJson('unit_results.json');
const contract = readJson('contract_results.json');
const property = readJson('property_results.json');
const e2e = readJson('e2e_results.json', { flaky_rate: 1 });
const axe = readJson('axe_results.json');
const lighthouse = readJson('lighthouse_results.json');
const visual = readJson('visual_results.json');
const hintJudge = readJson('hint_judge.json', { summary: { avg_score: 0 } });
const golden = readJson('golden_results.json', { correct_rate: 0 });

const testsPass = [lint, unit, contract, property, readJson('e2e_results.json'), visual].every((x) => x.pass === true);

const scorecard = {
  version: 'scorecard.v1',
  timestamp: new Date().toISOString(),
  tests: {
    pass: testsPass,
    lint: !!lint.pass,
    unit: !!unit.pass,
    contract: !!contract.pass,
    property: !!property.pass,
    e2e: !!readJson('e2e_results.json').pass,
    visual: !!visual.pass,
  },
  e2e: {
    flaky_rate: Number(e2e.flaky_rate || 0),
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

const schemaPath = join(process.cwd(), 'schemas', 'scorecard.schema.json');
const schema = JSON.parse(readFileSync(schemaPath, 'utf8'));
const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(schema);
if (!validate(scorecard)) {
  process.exit(1);
}

mkdirSync(join(process.cwd(), 'artifacts'), { recursive: true });
writeFileSync(join(process.cwd(), 'artifacts', 'scorecard.json'), JSON.stringify(scorecard, null, 2), 'utf8');
