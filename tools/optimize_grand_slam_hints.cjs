#!/usr/bin/env node
/**
 * optimize_grand_slam_hints.cjs
 * ─────────────────────────────
 * Optimise the 188-question g5-grand-slam bank.js hints for child-friendly clarity.
 *
 * Constraints:
 *   - NO hint may contain the final answer verbatim  (answer-leak guard)
 *   - Only g5-grand-slam/bank.js is modified; fraction-word-g5 is untouched.
 *   - L3 (currently 100% boilerplate) → specific per-kind calculation guidance
 *   - L1 / L2 enriched where too short (< 60 chars net)
 *
 * Usage:
 *   node tools/optimize_grand_slam_hints.cjs          # preview
 *   node tools/optimize_grand_slam_hints.cjs --apply  # write to bank.js
 */

'use strict';
const fs   = require('fs');
const path = require('path');

const BANK_PATH = path.resolve(__dirname, '..', 'docs', 'g5-grand-slam', 'bank.js');
const DIST_PATH = path.resolve(__dirname, '..', 'dist_ai_math_web_pages', 'docs', 'g5-grand-slam', 'bank.js');

const apply = process.argv.includes('--apply');

/* ── improved L3 templates keyed by kind ───────────────────────────── */
const L3_TEMPLATES = {
  // ─── 大單位換算 ───
  ha_to_m2:        '👉 算式方向：先寫出「?? × 10,000」，再數位數、確認 0 的個數是否正確，最後標上單位「平方公尺」。',
  km2_to_ha:       '👉 算式方向：先寫出「?? × 100」，注意小數乘 100 時小數點往右移兩位，最後標上「公頃」。',
  are_to_m2:       '👉 算式方向：先寫出「?? × 100」，乘 100 就是小數點右移兩位，記得標上「平方公尺」。',
  liter_to_ml:     '👉 算式方向：先寫「?? × 1000」，乘 1000 小數點右移三位，檢查位數後標上 mL。',
  cm3_to_ml:       '👉 1 cm³ 就是 1 mL，數值完全一樣。只要把數字原封不動寫上去，改標 mL 就完成了！',

  // ─── 小數乘法 ───
  decimal_times_integer: '👉 計算小撇步：先把小數當整數算（忽略小數點），得到結果後再把小數點放回去（往左移回原來的小數位數）。最後用估算驗算：答案大約在多少範圍？',
  decimal_times_decimal: '👉 計算小撇步：兩數都當整數相乘，得到整數積後，把「兩個數的小數位數加起來」，在乘積從右邊數這麼多位放上小數點。最後估算一下有沒有合理。',

  // ─── 分數加減 ───
  fraction_add_unlike: '👉 一步步算：① 找公倍數 → ② 各分數同×到那個公倍數 → ③ 分子相加 → ④ 看能不能約分變最簡分數。做完再驗算：通分回去看原式是否相等。',
  fraction_sub_mixed:  '👉 一步步算：① 帶分數化成假分數（整數×分母＋分子）→ ② 通分 → ③ 分子相減 → ④ 化回帶分數或最簡分數。驗算：把答案加回減掉的數，看是否等於被減數。',

  // ─── 整數×分數 ───
  int_times_fraction:   '👉 一步步算：把整數寫成「?/1」→ 分子乘分子、分母乘分母 → 看能不能約分。最後心算驗一下：整數 × 分子 ÷ 分母 ≈ 多少？',
  remaining_by_fraction:'👉 一步步算：① 先算「1 − 已用掉的分數」得到剩下的分數 → ② 再用「總量 × 剩下的分數」算出剩下多少 → ③ 驗算：剩下＋用掉 = 總量？',
  fraction_of_fraction: '👉 一步步算：「⋯的幾分之幾的幾分之幾」= 連續乘。先算第一段，再乘第二段。驗算：答案應該比原來的數小很多。',

  // ─── 分數×分數 ───
  fraction_times_fraction: '👉 一步步算：① 先看哪個分子和哪個分母可以交叉約分 → ② 約完再分子×分子、分母×分母 → ③ 最後確認是最簡分數。',

  // ─── 比率與百分率 ───
  find_percent:      '👉 一步步算：① 部分 ÷ 全體 = 小數 → ② 小數 × 100 = 百分率。驗算：百分率 × 全體 ÷ 100 應該等於部分。',
  percent_discount:  '👉 一步步算：① 找到「要付多少 %」→ ② 原價 × 該百分比 ÷ 100 → ③ 驗算：折後價應 < 原價。',
  percent_to_ppm:    '👉 換算訣竅：1% = 10,000 ppm。所以先把百分比數字 × 10,000 就好。驗算：答案是否看起來合理（比百分比的數字大很多）。',
  cheng_increase:    '👉 一步步算：① 把「加幾成」換成「加 ??%」→ ② 新價 = 原價 × (100 + ??)% → ③ 驗算：新價應該比原價大。',

  // ─── 體積/表面積 ───
  surface_area_rect_prism:      '👉 對對看：先算 3 個不同面的面積（長×寬、長×高、寬×高），加起來後再 ×2（因為每組有兩個一樣的面）。驗算：每個面的面積有沒有算錯。',
  surface_area_cube:            '👉 正方體每一面都一樣！先算一面（邊長×邊長），再 ×6 就是答案。驗算數字有沒有算錯。',
  surface_area_contact_removed: '👉 拆解想：先算全部的表面積（兩個物體各自的），再減掉被蓋住看不到的面（×2，兩面都看不到）。驗算：答案 < 兩個寶物獨立的表面積加起來。',
  displacement:      '👉 排水法超簡單：放進去後的水位 − 放進去前的水位 = 物體的體積。相減就好。',

  // ─── 時間計算 ───
  time_add_cross_day: '👉 一步步算：① 先把時間變成總分鐘數 → ② 加上要加的分鐘 → ③ 如果超過 1440（24 小時），就減掉 1440 → ④ 換回 HH:MM。',
  time_sub_cross_day: '👉 一步步算：① 先把時間變成總分鐘數 → ② 減掉要減的分鐘 → ③ 如果變成負數，就加上 1440（24 小時）→ ④ 換回 HH:MM。',
  time_multiply:      '👉 直接乘就好：每段 × 段數 = 總時間。如果超過 60 分鐘，記得換成「?? 小時 ?? 分」。',

  // ─── 因數與倍數 ───
  gcd_word:          '👉 找 GCD 方法：① 短除法或列因數法都可以 → ② 兩個數同時除以公因數，直到不能再除 → ③ 把除過的公因數全部乘起來。',
  lcm_word:          '👉 找 LCM 方法：① 用短除法把兩數同時除到互質 → ② 把除數和剩下的數全部乘起來。或列倍數找最小的相同倍數。',
  prime_or_composite:'👉 檢查方法：用 2、3、5、7… 一個一個試除。如果除到 √n 都沒有整除，就是質數。如果中間有一個整除了（而且不是 1 和自己），就是合數。',

  // ─── 大數與位值 ───
  place_value_truncate: '👉 無條件捨去策略：① 找到目標位（例如千萬位）→ ② 把那個位以下的數字全歸零 → 驗算：答案是否只在目標位及以上有數字。',
  place_value_yi_wan:   '👉 拆開算：① 億前面的數字 × 1 億 → ② 萬前面的數字 × 1 萬 → ③ 剩下的直接加上。最後數數有沒有少了哪段。',
  place_value_digit:    '👉 找位數方法：從右邊開始數（個→十→百→千→萬→十萬→百萬…），數到目標位，看上面是什麼數字。',

  // ─── 平面圖形 ───
  area_trapezoid:      '👉 套公式：(上底 + 下底) × 高 ÷ 2。小提醒：先算括號裡面，再乘高，最後除以 2。',
  area_triangle:       '👉 套公式：底 × 高 ÷ 2。先乘再除，如果乘出來是奇數，結果會有小數。',
  area_parallelogram:  '👉 套公式：底 × 高。注意「高」是垂直於底的距離，不是斜邊。',
  area_congruent_tile: '👉 想法：用全等概念 → 拼出的大圖形面積 ÷ 幾塊 = 一塊的面積。先算大圖形面積，再均分。',

  // ─── 線對稱 ───
  perp_bisector_property: '👉 口訣記住：「在中垂線上 → 到兩端等距」。這題只要想到這個性質就可以寫出答案了。',
  perp_bisector_converse: '👉 反過來也成立：「到兩端等距 → 在中垂線上」。記住：性質和逆敘述都是對的。',
  symmetry_axes:          '👉 想像方法：在腦中或紙上「對折」，每一種能對折重合的方向就是一條對稱軸。正方形有 4 條，長方形有 2 條。',

  // ─── 扇形與圓心角 ───
  sector_central_angle: '👉 套公式：圓心角 = 佔整個圓的分數 × 360°。先把分數算出小數，再 × 360。驗算：答案 ≤ 360°。',
  clock_angle:          '👉 時鐘口訣：分針位置 = 分鐘 × 6°；時針位置 = 小時 × 30° + 分鐘 × 0.5°。兩個角度的差就是夾角，如果差 > 180°，要用 360° 去減。',
  reciprocal:           '👉 倒數就是分子分母互換。整數 n 的倒數是 1/n。把答案乘回原來的數，看是不是 = 1 就對了。',

  // ─── 折線圖 ───
  line_trend:    '👉 看趨勢：比較指定時段開頭和結尾的數值，變大 → 上升，變小 → 下降，一樣 → 持平。',
  line_max_month:'👉 找最大值：把每個月的數字列出來，圈出最大的那個，它對應的月份就是答案。',
  line_omit_rule:'👉 等差規律：先算公差（第二項 − 第一項），然後每一項都加上公差。用公差驗算後面的項是否也符合。',

  // ─── 代數前導 ───
  solve_x_plus_a: '👉 移項口訣：「加的變減、減的變加」→ 把常數移到等號另一邊，x 就自己留下了。驗算：把答案代回去，左邊 = 右邊？',
  solve_ax:       '👉 移項口訣：「乘的變除、除的變乘」→ 兩邊同除以係數。驗算：把答案代回去，左邊 = 右邊？',
  solve_x_div_d:  '👉 要消掉除法，兩邊同乘那個除數。驗算：把答案代回去，左邊 = 右邊？',
};

/* ── L1 enrichments — only used when current L1 is too short (<60 net chars) ─ */
const L1_ENRICH = {
  ha_to_m2:        '⭐ 觀念提醒\n面積單位由「公頃」轉成「平方公尺」時，乘上 10,000。記住：1 公頃就是 100 公尺 × 100 公尺的正方形面積。',
  km2_to_ha:       '⭐ 觀念提醒\n1 平方公里 = 100 公頃。想像 1 公里 × 1 公里的大正方形，裡面放了 100 個 100m×100m 的小正方形。',
  are_to_m2:       '⭐ 觀念提醒\n1 公畝 = 100 平方公尺。公畝像個 10m × 10m 的小方塊。',
  liter_to_ml:     '⭐ 觀念提醒\n容量換算：1 公升 = 1000 毫升（mL）。L → mL 乘 1000，反過來除 1000。',
  cm3_to_ml:       '⭐ 觀念提醒\n體積 ↔ 容量：1 cm³ = 1 mL，數字相同，改單位就好。',
  displacement:    '⭐ 觀念提醒\n排水法測體積：放入前水量 vs 放入後水量，差值就是物體體積。',
  time_multiply:   '⭐ 觀念提醒\n「相同長度的時間做幾次」→ 時間 × 次數。超過 60 分鐘記得換成小時分鐘。',
  area_triangle:   '⭐ 觀念提醒\n三角形面積 = 底 × 高 ÷ 2。它是同底等高的平行四邊形或長方形的一半。',
  area_parallelogram:'⭐ 觀念提醒\n平行四邊形面積 = 底 × 高。把平行四邊形切一刀再拼，就會變成等面積的長方形。',
  reciprocal:      '⭐ 觀念提醒\n倒數 = 分子分母互換。任何數 × 它的倒數 = 1。整數 n 的倒數是 1/n。',
  symmetry_axes:   '⭐ 觀念提醒\n對稱軸就是摺線。把圖形沿著線對折，如果兩邊完全重合，那條線就是對稱軸。',
};

/* ── L2 enrichments — only used when current L2 is too short (<60 net chars) ─ */
const L2_ENRICH = {
  cm3_to_ml:       '🔍 列式引導\n因為 1 cm³ = 1 mL，所以直接把 cm³ 前面的數字搬過來就好，不用做任何計算。',
  displacement:    '🔍 列式引導\n列式超簡單：放入後水量 − 放入前水量 = 物體體積。找到兩個數字就可以減了。',
  time_multiply:   '🔍 列式引導\n列出乘法：每段時間 × 段數 = 總時間（分鐘）。如果題目要求用 HH:MM 回答，記得除以 60 換算。',
};

/* ──────────────────────────────────────────────────────────────── */

// Fallback L3 for any kind not in the table
const L3_FALLBACK = '👉 按照前兩步的觀念與列式，一步一步算。算完後問自己：答案的單位對嗎？數值有沒有大到不合理或太小？用估算再確認一次。';

// ── Read bank.js ──
const src = fs.readFileSync(BANK_PATH, 'utf8');
const bankMatch = src.match(/window\.G5_GRAND_SLAM_BANK\s*=\s*(\[[\s\S]*?\]);/);
if (!bankMatch) { console.error('Cannot parse bank.js'); process.exit(1); }
const bank = eval(bankMatch[1]);

/* ── helpers ── */
function netLen(s) { return (s || '').replace(/^Hint \d[｜|].*?\n/,'').trim().length; }

function containsAnswer(text, answer) {
  if (!text || answer == null) return false;
  const a = String(answer).trim();
  if (!a) return false;
  const t = text.replace(/[\s,，]/g, '');
  const aNorm = a.replace(/[\s,，]/g, '');
  // exact match as standalone token
  if (t.includes(aNorm)) {
    // allow very short numbers (1-2 digits) only if they appear as "= answer" pattern
    if (aNorm.length <= 2) {
      return new RegExp('=\\s*' + aNorm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?!\\d)').test(t);
    }
    return true;
  }
  return false;
}

/* ── Process ── */
let changed = 0;
let leakFixed = 0;

bank.forEach(q => {
  const kind = q.kind;
  let dirty = false;

  // ── L3: replace boilerplate ──
  const oldL3 = q.hints[2] || '';
  if (oldL3.includes('請依前面步驟完成計算') || oldL3.length < 30) {
    const template = L3_TEMPLATES[kind] || L3_FALLBACK;
    q.hints[2] = 'Hint 3｜計算引導\n' + template;
    dirty = true;
  }

  // ── L1: enrich if too short ──
  if (netLen(q.hints[0]) < 60 && L1_ENRICH[kind]) {
    q.hints[0] = L1_ENRICH[kind];
    dirty = true;
  }

  // ── L2: enrich if too short ──
  if (netLen(q.hints[1]) < 30 && L2_ENRICH[kind]) {
    q.hints[1] = L2_ENRICH[kind];
    dirty = true;
  }

  // ── answer-leak guard ──
  q.hints.forEach((h, i) => {
    if (containsAnswer(h, q.answer)) {
      // strip the leaked answer
      const a = String(q.answer).trim();
      const escaped = a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      q.hints[i] = h.replace(new RegExp('=\\s*' + escaped + '(?!\\d)', 'g'), '= ？？');
      leakFixed++;
      dirty = true;
    }
  });

  if (dirty) changed++;
});

/* ── Stats ── */
console.log('=== g5-grand-slam hint optimization ===');
console.log(`Questions modified: ${changed} / ${bank.length}`);
console.log(`Answer leaks fixed: ${leakFixed}`);

// Sample output
const sample = bank.find(q => q.kind === 'fraction_sub_mixed');
if (sample) {
  console.log('\n─── Sample (fraction_sub_mixed) ───');
  sample.hints.forEach((h, i) => console.log(`  L${i+1}: ${h.slice(0, 150)}`));
}
const sample2 = bank.find(q => q.kind === 'surface_area_rect_prism');
if (sample2) {
  console.log('\n─── Sample (surface_area_rect_prism) ───');
  sample2.hints.forEach((h, i) => console.log(`  L${i+1}: ${h.slice(0, 150)}`));
}

if (!apply) {
  console.log('\n(dry run — use --apply to write changes)');
  process.exit(0);
}

/* ── Write back ── */
const bankStr = JSON.stringify(bank, null, 2);
const newSrc = src.replace(bankMatch[0], `window.G5_GRAND_SLAM_BANK = ${bankStr};`);
fs.writeFileSync(BANK_PATH, newSrc, 'utf8');
console.log(`\n✅ Written: ${BANK_PATH}`);

// also write dist mirror
if (fs.existsSync(path.dirname(DIST_PATH))) {
  fs.writeFileSync(DIST_PATH, newSrc, 'utf8');
  console.log(`✅ Written: ${DIST_PATH}`);
}

console.log('\nDone. Run validation next:');
console.log('  python tools/validate_all_elementary_banks.py');
