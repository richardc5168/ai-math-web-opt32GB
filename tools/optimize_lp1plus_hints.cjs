#!/usr/bin/env node
/**
 * optimize_lp1plus_hints.cjs
 * ─────────────────────────
 * Batch-optimize hints for Life Pack 1+ (加強版) bank.
 *
 * Changes applied:
 *  1. Add emoji markers (🔍📊✏️🎯) to each hint level
 *  2. Replace boilerplate Level 4 with unit-specific verification prompts
 *  3. Soften Level 3 to avoid full-formula leaks (guide, don't solve)
 *
 * Safety:
 *  - Never modifies fraction-word-g5 (protected template)
 *  - Writes to both docs/ and dist/ mirrors
 *  - Dry-run mode by default: pass --apply to write
 */

'use strict';
const fs = require('fs');
const path = require('path');

const APPLY = process.argv.includes('--apply');
const BANK_PATHS = [
  path.join(__dirname, '..', 'docs', 'interactive-g5-life-pack1plus-empire', 'bank.js'),
  path.join(__dirname, '..', 'dist_ai_math_web_pages', 'docs', 'interactive-g5-life-pack1plus-empire', 'bank.js'),
];

// ── Unit-specific Level 4 verification prompts ──
const LEVEL4_BY_UNIT = {
  u1_avg_fraction:
    '🎯 驗算：把你的答案 × 人數，看是否等於原本的總量？單位是否合理？',
  u2_frac_addsub_life:
    '🎯 驗算：把結果代回題目「用掉/剩下」的敘述，數字是否吻合？分數是否已化為最簡？',
  u3_frac_times_int:
    '🎯 驗算：把答案 ÷ 整數倍數，應該回到原本的分數。結果合理嗎？',
  u4_money_decimal_addsub:
    '🎯 驗算：金額相加或相減後，小數點位數是否正確？幣值單位（元）有寫嗎？估算一下大小是否合理。',
  u5_decimal_muldiv_price:
    '🎯 驗算：用答案反推原題（乘↔除互逆），數字是否吻合？小數點位數對嗎？',
  u6_frac_dec_convert:
    '🎯 驗算：把分數和小數互換回去，兩邊是否相等？有無約分到最簡？',
  u7_discount_percent:
    '🎯 驗算：折後價應 < 原價（打折）或 > 原價（加成）。用「折後 ÷ 原價」算出折數，和題目吻合嗎？',
  u8_ratio_recipe:
    '🎯 驗算：各成分比例加起來是否 = 總量？倍率是否一致？用「份數 × 倍率」反推每份是否吻合。',
  u9_unit_convert_decimal:
    '🎯 驗算：換算方向對嗎（大單位→小單位要 ×，反之要 ÷）？小數點移動幾位是否正確？',
  u10_rate_time_distance:
    '🎯 驗算：用「路程 ÷ 時間 = 速率」三角關係互驗。單位是否統一（km/h、m/min…）？',
};

// ── Level 3 softening: remove direct formulas, keep guidance ──
// Generic guidance per unit (never reveals specific numbers)
const SOFT_L3_BY_UNIT = {
  u1_avg_fraction:
    '把「總量 ÷ 人數」列成分數除法，再化成乘以倒數來計算。最後約分到最簡。',
  u2_frac_addsub_life:
    '先通分（找兩個分母的最小公倍數），再做加法或減法。結果記得約分。',
  u3_frac_times_int:
    '分數 × 整數：分子 × 整數，分母不變，最後記得約分到最簡。',
  u4_money_decimal_addsub:
    '小數對齊小數點後直行加減，位數不夠的補 0 對齊。答案記得寫單位（元）。',
  u5_decimal_muldiv_price:
    '先當整數算出結果，再數兩邊小數位數總和，放回小數點。',
  u6_frac_dec_convert:
    '分數→小數：分子÷分母；小數→分數：看位數寫分母（10/100/1000），再約分。',
  u7_discount_percent:
    '「打 N 折」= 原價 × (N÷10)。先把折數換成小數倍率，再和原價相乘。',
  u8_ratio_recipe:
    '每份量 = 總量 ÷ 總份數。先算出「每份」再乘以需要的份數。',
  u9_unit_convert_decimal:
    '大→小：乘（小數點右移）；小→大：除（小數點左移）。數好要移幾位。',
  u10_rate_time_distance:
    '路程 = 速率 × 時間。先確認哪兩個已知，求第三個；注意單位要統一。',
};

function hasLeakRisk(hint, answer) {
  const ans = String(answer);
  // Direct formula patterns that reveal answer
  if (/列式[：:]/.test(hint)) return true;
  // Contains "= number" where number matches answer
  if (hint.includes('=' + ans) || hint.includes('= ' + ans)) return true;
  // Contains explicit "AxB=C" or "A÷B=C" calculation
  if (/\d+[×÷]\d+\s*=\s*\d+/.test(hint)) return true;
  // Contains "= N×M" or "= N÷M" (full formula after equals)
  if (/=\s*\d+[.\/]?\d*\s*[×÷]\s*\d+/.test(hint)) return true;
  // Contains specific discount/rate like "N折就是" with number
  if (/\d+\s*折就是/.test(hint)) return true;
  // Starts with a specific number (too formulaic)
  if (/^\d+/.test(hint)) return true;
  // Contains the exact answer as a standalone number
  const ansNum = parseFloat(ans);
  if (!isNaN(ansNum)) {
    const calcMatch = hint.match(/=\s*([\d./]+)/g);
    if (calcMatch) {
      for (const cm of calcMatch) {
        const val = cm.replace(/^=\s*/, '');
        if (val === ans || parseFloat(val) === ansNum) return true;
      }
    }
  }
  return false;
}

function softenLevel3(hint, kind, question, answer) {
  let h = hint;

  // Remove existing emoji prefix
  h = h.replace(/^[✏️📊🔍🎯]\s*/, '');

  // Always use generic guidance if there's any leak risk
  if (hasLeakRisk(h, answer) && SOFT_L3_BY_UNIT[kind]) {
    h = SOFT_L3_BY_UNIT[kind];
  } else if (SOFT_L3_BY_UNIT[kind]) {
    // Even without leak, if hint is too similar to boilerplate, enrich
    // Check if hint is very short (< 15 chars) or too formulaic
    if (h.length < 15 || /^\d/.test(h)) {
      h = SOFT_L3_BY_UNIT[kind];
    }
    // Otherwise keep original hint (it's already good guidance)
  }

  return '✏️ ' + h;
}

// ── Add emoji prefix to Level 1 & 2 ──
function addEmojiL1(hint) {
  let h = hint.replace(/^[🔍📊✏️🎯]\s*/, '');
  return '🔍 ' + h;
}

function addEmojiL2(hint) {
  let h = hint.replace(/^[🔍📊✏️🎯]\s*/, '');
  return '📊 ' + h;
}

// ── Main transform ──
function transformBank(bankPath) {
  const src = fs.readFileSync(bankPath, 'utf8');
  const match = src.match(/(window\.\w+\s*=\s*)(\[[\s\S]*?\]);/);
  if (!match) {
    console.error('  ❌ Cannot parse bank array in', bankPath);
    return { changed: 0, total: 0 };
  }

  const prefix = match[1];
  const bank = JSON.parse(match[2]);
  let changed = 0;

  for (const q of bank) {
    if (!q.hints || q.hints.length < 4) continue;

    const origHints = [...q.hints];
    const kind = q.kind;

    // Level 1: add 🔍 if missing
    if (!q.hints[0].startsWith('🔍')) {
      q.hints[0] = addEmojiL1(q.hints[0]);
    }

    // Level 2: add 📊 if missing
    if (!q.hints[1].startsWith('📊')) {
      q.hints[1] = addEmojiL2(q.hints[1]);
    }

    // Level 3: soften + add ✏️
    if (!q.hints[2].startsWith('✏️')) {
      q.hints[2] = softenLevel3(q.hints[2], kind, q.question, q.answer);
    }

    // Level 4: replace boilerplate with unit-specific verification
    const isBoilerplate = q.hints[3].includes('請依前面步驟完成計算');
    if (isBoilerplate && LEVEL4_BY_UNIT[kind]) {
      q.hints[3] = LEVEL4_BY_UNIT[kind];
    } else if (!q.hints[3].startsWith('🎯')) {
      q.hints[3] = '🎯 ' + q.hints[3].replace(/^[🔍📊✏️🎯]\s*/, '');
    }

    // Check if anything changed
    if (JSON.stringify(origHints) !== JSON.stringify(q.hints)) {
      changed++;
    }
  }

  if (APPLY) {
    const output = prefix + JSON.stringify(bank, null, 2) + ';\n';
    fs.writeFileSync(bankPath, output, 'utf8');
    console.log(`  ✅ Written ${bankPath} (${changed}/${bank.length} questions updated)`);
  } else {
    console.log(`  [DRY-RUN] Would update ${changed}/${bank.length} questions in ${path.basename(path.dirname(bankPath))}`);
    // Show sample changes
    const sample = bank.find(q => q.kind === 'u7_discount_percent');
    if (sample) {
      console.log('  Sample (u7):', JSON.stringify(sample.hints, null, 2));
    }
  }

  return { changed, total: bank.length };
}

// ── Run ──
console.log(`\n=== LP1+ Hint Optimizer ${APPLY ? '(APPLY MODE)' : '(DRY-RUN, pass --apply to write)'} ===\n`);

let totalChanged = 0;
for (const p of BANK_PATHS) {
  if (!fs.existsSync(p)) {
    console.log(`  ⚠️ File not found: ${p}`);
    continue;
  }
  console.log(`Processing: ${path.relative(path.join(__dirname, '..'), p)}`);
  const { changed } = transformBank(p);
  totalChanged += changed;
}

console.log(`\nTotal questions modified: ${totalChanged}`);
if (!APPLY) {
  console.log('Run with --apply to write changes.');
}
