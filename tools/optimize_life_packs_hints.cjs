#!/usr/bin/env node
/**
 * optimize_life_packs_hints.cjs
 * ─────────────────────────────
 * Batch-optimize hints for ALL Life Pack empire modules:
 *   - Life Pack 1 (200q, 4-level, G5_LIFE_PACK1_BANK)
 *   - Life Pack 2 (200q, 4-level, G5_LIFE_PACK2_BANK)
 *   - Life Pack 2+ (250q, 3-level, G5_LIFE_PACK2PLUS_BANK)
 *
 * Changes:
 *  1. Add emoji markers (🔍📊✏️ + 🎯 for 4-level)
 *  2. Replace boilerplate L4 with unit-specific verification
 *  3. Soften L3 leak risk (guide, don't solve)
 *
 * DOES NOT touch: fraction-word-g5 (protected), LP1+ (already done)
 */

'use strict';
const fs = require('fs');
const path = require('path');

const APPLY = process.argv.includes('--apply');
const ROOT = path.join(__dirname, '..');

// ── Modules to process ──
const MODULES = [
  {
    dir: 'interactive-g5-life-pack1-empire',
    varName: 'G5_LIFE_PACK1_BANK',
    levels: 4,
  },
  {
    dir: 'interactive-g5-life-pack2-empire',
    varName: 'G5_LIFE_PACK2_BANK',
    levels: 4,
  },
  {
    dir: 'interactive-g5-life-pack2plus-empire',
    varName: 'G5_LIFE_PACK2PLUS_BANK',
    levels: 3,
  },
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

// Fallback for 3-level modules or unknown kinds
const LEVEL4_FALLBACK =
  '🎯 驗算：把答案代回題目敘述，數字是否吻合？單位是否正確？估算一下大小是否合理。';

// ── Generic L3 guidance by unit (no answer leaks) ──
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
  if (/列式[：:]/.test(hint)) return true;
  if (hint.includes('=' + ans) || hint.includes('= ' + ans)) return true;
  if (/\d+[×÷]\d+\s*=\s*\d+/.test(hint)) return true;
  if (/=\s*\d+[.\/]?\d*\s*[×÷]\s*\d+/.test(hint)) return true;
  if (/\d+\s*折就是/.test(hint)) return true;
  if (/^\d+/.test(hint)) return true;
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

function transformBank(bankPath, levels) {
  const src = fs.readFileSync(bankPath, 'utf8');
  const match = src.match(/(window\.\w+\s*=\s*)(\[[\s\S]*?\]);/);
  if (!match) {
    console.error('  ❌ Cannot parse bank in', bankPath);
    return 0;
  }

  const prefix = match[1];
  const bank = JSON.parse(match[2]);
  let changed = 0;

  for (const q of bank) {
    if (!q.hints || q.hints.length < levels) continue;
    const orig = JSON.stringify(q.hints);
    const kind = q.kind;

    // L1: 🔍
    if (!q.hints[0].startsWith('🔍')) {
      q.hints[0] = '🔍 ' + q.hints[0].replace(/^[🔍📊✏️🎯]\s*/, '');
    }

    // L2: 📊
    if (!q.hints[1].startsWith('📊')) {
      q.hints[1] = '📊 ' + q.hints[1].replace(/^[🔍📊✏️🎯]\s*/, '');
    }

    // L3 (last level for 3-level, or penultimate for 4-level): ✏️ + soften
    const l3idx = levels >= 4 ? 2 : 2; // always index 2
    if (!q.hints[l3idx].startsWith('✏️')) {
      let h = q.hints[l3idx].replace(/^[🔍📊✏️🎯]\s*/, '');
      if (hasLeakRisk(h, q.answer) && SOFT_L3_BY_UNIT[kind]) {
        h = SOFT_L3_BY_UNIT[kind];
      } else if (h.length < 15 || /^\d/.test(h)) {
        h = SOFT_L3_BY_UNIT[kind] || h;
      }
      q.hints[l3idx] = '✏️ ' + h;
    }

    // L4 (only for 4-level): 🎯 + unit-specific verification
    if (levels >= 4 && q.hints.length >= 4) {
      const isBoilerplate = q.hints[3].includes('請依前面步驟完成計算');
      if (isBoilerplate) {
        q.hints[3] = LEVEL4_BY_UNIT[kind] || LEVEL4_FALLBACK;
      } else if (!q.hints[3].startsWith('🎯')) {
        q.hints[3] = '🎯 ' + q.hints[3].replace(/^[🔍📊✏️🎯]\s*/, '');
      }
    }

    if (JSON.stringify(q.hints) !== orig) changed++;
  }

  if (APPLY) {
    const output = prefix + JSON.stringify(bank, null, 2) + ';\n';
    fs.writeFileSync(bankPath, output, 'utf8');
    console.log(`  ✅ ${changed}/${bank.length} updated`);
  } else {
    console.log(`  [DRY] ${changed}/${bank.length} would change`);
  }
  return changed;
}

// ── Main ──
console.log(`\n=== Life Packs Hint Optimizer ${APPLY ? '(APPLY)' : '(DRY-RUN)'} ===\n`);

let total = 0;
for (const mod of MODULES) {
  console.log(`\n--- ${mod.dir} (${mod.levels}-level) ---`);
  for (const base of ['docs', 'dist_ai_math_web_pages/docs']) {
    const p = path.join(ROOT, base, mod.dir, 'bank.js');
    if (!fs.existsSync(p)) { console.log(`  ⚠️ ${base} not found`); continue; }
    console.log(`  ${base}:`);
    total += transformBank(p, mod.levels);
  }
}

console.log(`\nTotal changes: ${total}`);
if (!APPLY) console.log('Pass --apply to write.');
