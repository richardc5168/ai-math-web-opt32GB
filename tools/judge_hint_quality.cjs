const fs = require('fs');
const path = require('path');
const { writeJson } = require('./_runner.cjs');

function readJsonl(filePath) {
  return fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function hasAny(text, words) {
  const t = String(text || '');
  return words.some((w) => t.includes(w));
}

function scoreItem(q) {
  const h1 = q.hint_ladder?.h1_strategy || '';
  const h2 = q.hint_ladder?.h2_equation || '';
  const h3 = q.hint_ladder?.h3_compute || '';
  const h4 = q.hint_ladder?.h4_check_reflect || '';

  const strategy = hasAny(h1, ['折扣', '平均', '單位', '路程', '比例', '分數']) ? 2 : (h1.length > 8 ? 1 : 0);
  const equation = hasAny(h2, ['=', '×', '÷', '+', '-', '→']) ? 2 : (h2.length > 8 ? 1 : 0);
  const compute = hasAny(h3, ['先', '再', '最後', '步', '→', '=']) ? 2 : (h3.length > 8 ? 1 : 0);
  const misconception = (q.report_expectations?.misconceptions || []).length >= 1 ? 2 : 0;
  const check = hasAny(h4, ['檢查', '合理', '反思', '估算']) ? 2 : (h4.length > 8 ? 1 : 0);

  const score = strategy + equation + compute + misconception + check;
  const notes = [];
  if (check < 2) notes.push('h4可更具體');
  if (equation < 2) notes.push('h2列式可再明確');

  return {
    id: q.id,
    score,
    breakdown: { strategy, equation, compute, misconception, check },
    notes,
  };
}

const inputPath = process.argv[2] || path.join(process.cwd(), 'golden', 'grade5_pack_v1.jsonl');
const outPathArg = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : null;
const questions = readJsonl(inputPath);
const items = questions.map(scoreItem);
const avg = items.reduce((n, it) => n + it.score, 0) / Math.max(items.length, 1);
const min = items.reduce((m, it) => Math.min(m, it.score), Number.POSITIVE_INFINITY);

const out = {
  summary: {
    avg_score: Number(avg.toFixed(2)),
    min_score: Number((Number.isFinite(min) ? min : 0).toFixed(2)),
    count: items.length,
  },
  items,
};

const outputName = outPathArg ? path.basename(outPathArg) : 'hint_judge.json';
writeJson(outputName, out);
console.log('hint judge done');
