const fs = require('fs');
const path = require('path');
const Ajv = require('ajv');
const { pythonCmd, runCommand, writeJson } = require('./_runner.cjs');

function readJsonl(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean);
  return lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (e) {
      throw new Error(`JSONL parse error at line ${idx + 1}: ${e.message}`);
    }
  });
}

const goldenPath = path.join(process.cwd(), 'golden', 'grade5_pack_v1.jsonl');
const schemaPath = path.join(process.cwd(), 'schemas', 'question.schema.json');
const questions = readJsonl(goldenPath);
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));

const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(schema);

const errors = [];
for (const q of questions) {
  const ok = validate(q);
  if (!ok) {
    errors.push({ id: q.id || 'unknown', errors: validate.errors });
    continue;
  }
  if (!Array.isArray(q.common_wrong_answers) || q.common_wrong_answers.length < 2) {
    errors.push({ id: q.id, errors: ['common_wrong_answers must contain at least 2 entries'] });
  }
}

const py = pythonCmd();
const elementary = runCommand(py, ['tools/validate_all_elementary_banks.py']);
const elementaryPass = elementary.pass;

const pass = errors.length === 0 && elementaryPass;
const out = {
  pass,
  goldenCount: questions.length,
  schemaErrors: errors,
  elementaryValidation: elementary,
};

writeJson('contract_results.json', out);
if (!pass) process.exit(1);
console.log('schema/contract checks passed');
