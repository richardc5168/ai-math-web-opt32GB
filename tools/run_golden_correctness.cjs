const fs = require('fs');
const path = require('path');
const { writeJson } = require('./_runner.cjs');

const lines = fs.readFileSync(path.join(process.cwd(), 'golden', 'grade5_pack_v1.jsonl'), 'utf8')
  .split(/\r?\n/)
  .filter(Boolean);

let ok = 0;
const issues = [];
for (const line of lines) {
  const q = JSON.parse(line);
  const hasAnswer = String(q.answer || '').trim().length > 0;
  const wrongs = Array.isArray(q.common_wrong_answers) ? q.common_wrong_answers : [];
  const distinctWrongs = wrongs.filter((w) => String(w).trim() !== String(q.answer).trim());
  if (hasAnswer && distinctWrongs.length >= 2) ok += 1;
  else issues.push({ id: q.id, reason: 'missing answer or insufficient wrong answers' });
}

const correctRate = lines.length ? ok / lines.length : 0;
const out = {
  pass: correctRate === 1,
  total: lines.length,
  ok,
  correct_rate: Number(correctRate.toFixed(4)),
  issues,
};

writeJson('golden_results.json', out);
if (!out.pass) process.exit(1);
console.log('golden correctness passed');
