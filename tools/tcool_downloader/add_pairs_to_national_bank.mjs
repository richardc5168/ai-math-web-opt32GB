#!/usr/bin/env node
/**
 * Append browse-only tcool pairs into national G5 bank.
 *
 * Input:
 *  - downloads/paired_manifest.json
 *
 * Output:
 *  - docs/interactive-g5-national-bank/bank.js
 *  - dist_ai_math_web_pages/docs/interactive-g5-national-bank/bank.js
 *
 * Rules:
 *  - Only append items with status === browse_only_pair
 *  - Skip exam_ids already present (id: g5_national_source_<exam_id>)
 *  - Keep existing questions untouched
 */
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT = process.cwd();
const PAIRED = path.join(ROOT, 'downloads', 'paired_manifest.json');
const TARGETS = [
  path.join(ROOT, 'docs', 'interactive-g5-national-bank', 'bank.js'),
  path.join(ROOT, 'dist_ai_math_web_pages', 'docs', 'interactive-g5-national-bank', 'bank.js'),
];

const MAX_APPEND = Number(process.env.NATIONAL_BANK_APPEND_MAX || '100');

function parseBankJs(text) {
  const m = text.match(/window\.FRACTION_WORD_G5_BANK\s*=\s*(\[[\s\S]*\])\s*;\s*$/);
  if (!m) throw new Error('Cannot parse bank.js array payload');
  return JSON.parse(m[1]);
}

function toBankJs(arr) {
  return `window.FRACTION_WORD_G5_BANK = ${JSON.stringify(arr, null, 2)};\n`;
}

function buildSourceItem(pair) {
  const examId = String(pair.exam_id || '').trim();
  return {
    id: `g5_national_source_${examId}`,
    kind: 'national_bank_source',
    difficulty: 'medium',
    manual_check: true,
    question: `【全國來源卷 ${examId}】請開啟題目卷完成作答，再用解答卷核對。`,
    answer: '請依來源解答核對',
    source_question_url: String(pair.question_url || ''),
    source_answer_url: String(pair.answer_url || ''),
    steps: [
      '🔍 Level 1：先圈關鍵字（總量、單位、問什麼）。',
      '📊 Level 2：把題目拆成 2~3 個可計算步驟後列式。',
      '✏️ Level 3：先估算再精算，最後做一次反算。',
      '🎯 Level 4：開啟解答卷核對每一步差異，再修正。',
    ],
  };
}

async function main() {
  const paired = JSON.parse(await fs.readFile(PAIRED, 'utf8'));
  const candidates = paired.filter((x) => String(x.status) === 'browse_only_pair');

  for (const file of TARGETS) {
    const raw = await fs.readFile(file, 'utf8');
    const bank = parseBankJs(raw);
    const existed = new Set(
      bank
        .map((q) => String(q?.id || ''))
        .filter((id) => id.startsWith('g5_national_source_'))
        .map((id) => id.replace('g5_national_source_', ''))
    );

    const append = [];
    for (const pair of candidates) {
      const examId = String(pair.exam_id || '').trim();
      if (!examId) continue;
      if (existed.has(examId)) continue;
      append.push(buildSourceItem(pair));
      existed.add(examId);
      if (append.length >= MAX_APPEND) break;
    }

    if (append.length > 0) {
      bank.push(...append);
      await fs.writeFile(file, toBankJs(bank), 'utf8');
    }

    console.log(`${path.relative(ROOT, file)}: appended ${append.length} source items`);
  }
}

main().catch((err) => {
  console.error('add_pairs_to_national_bank failed:', err?.message || err);
  process.exit(1);
});
