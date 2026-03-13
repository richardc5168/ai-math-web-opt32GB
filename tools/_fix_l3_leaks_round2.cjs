#!/usr/bin/env node
/**
 * Fix 9 clear L3 hint leaks found by audit_hint_clarity.cjs.
 * Each fix replaces the leaked answer in hints[2] with "？".
 */
'use strict';
const fs = require('fs');
const path = require('path');

function fixBank(bankPath, fixes) {
  if (!fs.existsSync(bankPath)) { console.log('SKIP', bankPath); return 0; }
  const src = fs.readFileSync(bankPath, 'utf8');
  const window = {};
  new Function('window', src)(window);
  const varMatch = src.match(/window\.(\w+)\s*=/);
  const varName = varMatch[1];
  const bank = window[varName];
  let count = 0;
  for (const q of bank) {
    if (fixes[q.id]) {
      const f = fixes[q.id];
      q.hints[f.idx] = f.hint;
      count++;
    }
  }
  if (count > 0) {
    const out = 'window.' + varName + ' = ' + JSON.stringify(bank, null, 2) + ';\n';
    fs.writeFileSync(bankPath, out, 'utf8');
    console.log('  Fixed ' + count + ' in ' + bankPath);
  }
  return count;
}

// ─── Fix definitions ─────────────────────────────────────────

const gslamFixes = {
  'g5gs_time_mul_10': {
    idx: 2,
    hint: "📐 動手算：\n① 25 × 4 = 100 分鐘\n② 100 ÷ 60 = 1...40\n③ 換算成 → ？小時？分鐘 ✅"
  }
};

const midFixes = {
  'g5_midterm1_q39': {
    idx: 2,
    hint: "📐 一步步算：\n① 126 ÷ 9\n② 想想 9 × ？ = 126\n③ 每人分到 ？ 顆\n驗算：？ × 9 = 126 ✅"
  }
};

const natFixes = {
  'g5_national_exp_29': {
    idx: 2,
    hint: "📐 一步步算：\n① 195 ÷ 15\n② 想想 15 × ？ = 195\n③ 每人 ？ 本"
  },
  'g5_national_exp_30': {
    idx: 2,
    hint: "📐 一步步算：\n① 342 ÷ 18\n② 想想 18 × ？ = 342\n③ 可裝 ？ 箱"
  },
  'g5_national_exp_32': {
    idx: 2,
    hint: "📐 一步步算：\n① 156 ÷ 12\n② 想想 12 × ？ = 156\n③ 可買 ？ 個"
  }
};

const offlineFixes = {
  'offline_dec-034': {
    idx: 2,
    hint: "📐 一步步算：\n① 6+4=10進1\n① 0+9+1=10進1\n① 0+9+1=10進1\n① 12+3+1=？\n① = ?\n算完記得回頭檢查喔！✅"
  },
  'offline_dist-036': {
    idx: 2,
    hint: "📐 一步步算：\n① 80×3=？公里\n① 距離=?\n算完記得回頭檢查喔！✅"
  },
  'offline_dist-041': {
    idx: 2,
    hint: "📐 一步步算：\n① 1200÷80=？\n① 走?分鐘\n算完記得回頭檢查喔！✅"
  },
  'offline_dec-040': {
    idx: 2,
    hint: "📐 一步步算：\n① 一位小數→？\n算完記得回頭檢查喔！✅"
  }
};

// ─── Apply fixes ─────────────────────────────────────────────

const bankSets = [
  ['g5-grand-slam', gslamFixes],
  ['interactive-g5-midterm1', midFixes],
  ['interactive-g5-national-bank', natFixes],
  ['offline-math', offlineFixes],
];

let total = 0;
for (const [mod, fixes] of bankSets) {
  console.log('[' + mod + ']');
  const p1 = path.join(__dirname, '..', 'docs', mod, 'bank.js');
  const p2 = path.join(__dirname, '..', 'dist_ai_math_web_pages', 'docs', mod, 'bank.js');
  total += fixBank(p1, fixes);
  total += fixBank(p2, fixes);
}

console.log('\nTotal fixes applied: ' + total);
console.log('Run validator to verify.');
