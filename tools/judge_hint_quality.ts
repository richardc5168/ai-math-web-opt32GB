import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { basename, join } from 'path';

type GoldenQuestion = {
  id: string;
  report_expectations?: { misconceptions?: string[] };
  hint_ladder?: {
    h1_strategy?: string;
    h2_equation?: string;
    h3_compute?: string;
    h4_check_reflect?: string;
  };
};

function readJsonl(filePath: string): GoldenQuestion[] {
  return readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function hasAny(text: string, words: string[]): boolean {
  return words.some((word) => text.includes(word));
}

function scoreItem(q: GoldenQuestion) {
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
  const notes: string[] = [];
  if (check < 2) notes.push('h4可更具體');
  if (equation < 2) notes.push('h2列式可再明確');

  return {
    id: q.id,
    score,
    breakdown: { strategy, equation, compute, misconception, check },
    notes,
  };
}

const inputPath = process.argv[2] || join(process.cwd(), 'golden', 'grade5_pack_v1.jsonl');
const outArgIndex = process.argv.indexOf('--out');
const outPathArg = outArgIndex >= 0 ? process.argv[outArgIndex + 1] : '';
const outName = outPathArg ? basename(outPathArg) : 'hint_judge.json';
const outPath = join(process.cwd(), 'artifacts', outName);

const items = readJsonl(inputPath).map(scoreItem);
const avg = items.reduce((sum, item) => sum + item.score, 0) / Math.max(items.length, 1);
const min = items.reduce((minScore, item) => Math.min(minScore, item.score), Number.POSITIVE_INFINITY);

const out = {
  summary: {
    avg_score: Number(avg.toFixed(2)),
    min_score: Number((Number.isFinite(min) ? min : 0).toFixed(2)),
    count: items.length,
  },
  items,
};

mkdirSync(join(process.cwd(), 'artifacts'), { recursive: true });
writeFileSync(outPath, JSON.stringify(out, null, 2), 'utf8');
