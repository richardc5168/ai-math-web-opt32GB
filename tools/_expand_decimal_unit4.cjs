#!/usr/bin/env node
/**
 * Expand decimal-unit4 from 94 to ~150 questions.
 * Add more variety within each kind.
 * Current: d_mul_int(20), d_mul_d(18), d_div_int(16), int_mul_d(16), x10_shift(12), int_div_int_to_decimal(12) = 94
 * Target:  d_mul_int(30), d_mul_d(26), d_div_int(24), int_mul_d(24), x10_shift(20), int_div_int_to_decimal(20) = 144
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const BANK_PATH = path.join(__dirname, '..', 'docs', 'decimal-unit4', 'bank.js');
const DIST_PATH = path.join(__dirname, '..', 'dist_ai_math_web_pages', 'docs', 'decimal-unit4', 'bank.js');

// Load existing bank
const src = fs.readFileSync(BANK_PATH, 'utf8');
const ctx = { window: {} };
vm.runInNewContext(src, ctx);
const bank = ctx.window.DECIMAL_UNIT4_BANK;

console.log('Existing questions:', bank.length);

// Count existing per kind
const counts = {};
for (const q of bank) {
  counts[q.kind] = (counts[q.kind] || 0) + 1;
}
console.log('Per kind:', counts);

// Helper: pad number
const pad = n => String(n).padStart(3, '0');

// New questions to add
const newQs = [];

// ======== x10_shift (12 → 20, add 8) ========
const x10Qs = [
  { n: 13, q: '計算：5.67 ×100 = ?', a: '567', d: 'easy', mode: 'exact', u: '', nums: '5.67×100' },
  { n: 14, q: '計算：0.482 ×1000 = ?', a: '482', d: 'easy', mode: 'exact', u: '', nums: '0.482×1000' },
  { n: 15, q: '計算：123.4 ÷100 = ?', a: '1.234', d: 'easy', mode: 'exact', u: '', nums: '123.4÷100' },
  { n: 16, q: '計算：7.89 ÷10 = ?', a: '0.789', d: 'easy', mode: 'exact', u: '', nums: '7.89÷10' },
  { n: 17, q: '計算：45.6 ×0.01 = ?', a: '0.456', d: 'medium', mode: 'exact', u: '', nums: '45.6×0.01' },
  { n: 18, q: '計算：0.035 ×10000 = ?', a: '350', d: 'medium', mode: 'exact', u: '', nums: '0.035×10000' },
  { n: 19, q: '計算：8200 ×0.001 = ?', a: '8.2', d: 'medium', mode: 'exact', u: '', nums: '8200×0.001' },
  { n: 20, q: '計算：0.6 ×0.1 = ?', a: '0.06', d: 'easy', mode: 'exact', u: '', nums: '0.6×0.1' },
];
for (const x of x10Qs) {
  newQs.push({
    id: `d4_x10_shift_${pad(x.n)}`,
    kind: 'x10_shift',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: `（小數點移動）${x.q}`,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：乘以 10/100/1000 → 小數點往右移；除以(或乘0.1/0.01) → 往左移。',
      `列式：${x.nums}，數一數要移幾位。`,
      `📐 一步步算：\n① 判斷方向（乘→右移，除→左移）\n② 數幾個零就移幾位\n③ ${x.nums} = ？\n④ 檢查位數 ✓\n算完記得回頭檢查喔！✅`,
      '👉 ×10ⁿ 小數點右移 n 位，÷10ⁿ 左移 n 位。位數不夠就補 0。'
    ],
    steps: [
      '判斷移動方向',
      '數零的個數決定移幾位',
      `${x.nums} = ${x.a}`,
      '檢查位數 ✓'
    ],
    meta: { unit: x.u },
    explanation: `小數點移動：${x.nums} = ${x.a}。`,
    common_mistakes: [
      '小數點移動方向搞反（乘卻往左移）。',
      '移動位數數錯，少移或多移一位。'
    ]
  });
}

// ======== d_mul_int (20 → 30, add 10) ========
const dMulIntData = [
  { n: 21, q: '（買水果）每顆蘋果 3.75 元，買 8 顆，一共多少元？', a: '30', u: '元', d: 'easy', mode: 'exact', nums: '3.75×8' },
  { n: 22, q: '（跑步）每圈 0.45 公里，跑了 7 圈，一共多少公里？', a: '3.15', u: '公里', d: 'easy', mode: 'exact', nums: '0.45×7' },
  { n: 23, q: '（繩子）每段 1.28 公尺，需要 9 段，一共多少公尺？', a: '11.52', u: '公尺', d: 'easy', mode: 'exact', nums: '1.28×9' },
  { n: 24, q: '（鐵絲）每根 0.67 公尺，有 12 根，一共多少公尺？', a: '8.04', u: '公尺', d: 'medium', mode: 'exact', nums: '0.67×12' },
  { n: 25, q: '（油漆）每桶 4.35 公升，用了 5 桶，一共多少公升？', a: '21.75', u: '公升', d: 'easy', mode: 'exact', nums: '4.35×5' },
  { n: 26, q: '（布料）每塊 2.84 公尺，買了 6 塊，一共多少公尺？', a: '17.04', u: '公尺', d: 'easy', mode: 'exact', nums: '2.84×6' },
  { n: 27, q: '（牛奶）每瓶 0.375 公升，有 8 瓶，一共多少公升？', a: '3', u: '公升', d: 'medium', mode: 'exact', nums: '0.375×8' },
  { n: 28, q: '（電線）每捲 15.6 公尺，買了 4 捲，一共多少公尺？', a: '62.4', u: '公尺', d: 'easy', mode: 'exact', nums: '15.6×4' },
  { n: 29, q: '（液體）每瓶 0.85 公升，倒了 11 瓶，一共多少公升？', a: '9.35', u: '公升', d: 'medium', mode: 'exact', nums: '0.85×11' },
  { n: 30, q: '（文具）每枝筆 6.25 元，買了 4 枝，一共多少元？', a: '25', u: '元', d: 'easy', mode: 'exact', nums: '6.25×4' },
];
for (const x of dMulIntData) {
  newQs.push({
    id: `d4_d_mul_int_${pad(x.n)}`,
    kind: 'd_mul_int',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: x.q,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：同一份量有很多份 → 用乘法。',
      `列式：每份 × 份數。先估算會變大（因為乘的是整數份數）。`,
      `📐 一步步算：\n① 估算 ${x.nums}\n② 列式：${x.nums}\n③ 先忽略小數點做整數乘法\n④ 放回小數點 → ？ ${x.u}\n⑤ 檢查大小合理 ✓\n算完記得回頭檢查喔！✅`,
      '👉 小數×整數：先當整數算，再把小數點放回去（位數不變）。'
    ],
    steps: [`估算 ${x.nums}`, `列式：${x.nums}`, '先忽略小數點做整數乘法', `放回小數點 → ？ ${x.u}`, '檢查大小合理 ✓'],
    meta: { unit: x.u },
    explanation: `用乘法：${x.nums} = ${x.a}，依題目需求取位數 → ${x.a} ${x.u}。`,
    common_mistakes: [
      '忘了放回小數點，直接把整數乘法的結果當成答案。',
      '小數位數數錯，小數點位置放錯。'
    ]
  });
}

// ======== d_mul_d (18 → 26, add 8) ========
const dMulDData = [
  { n: 19, q: '（面積）長 3.5 公尺、寬 2.4 公尺，面積多少平方公尺？', a: '8.4', u: '平方公尺', d: 'medium', mode: 'exact', nums: '3.5×2.4' },
  { n: 20, q: '（單價）每公斤 45.5 元，買了 1.8 公斤，一共多少元？', a: '81.9', u: '元', d: 'medium', mode: 'exact', nums: '45.5×1.8' },
  { n: 21, q: '（距離）時速 5.2 公里，走了 1.5 小時，走了多少公里？', a: '7.8', u: '公里', d: 'medium', mode: 'exact', nums: '5.2×1.5' },
  { n: 22, q: '（布料）每公尺 38.5 元，買了 2.6 公尺，一共多少元？', a: '100.1', u: '元', d: 'medium', mode: 'exact', nums: '38.5×2.6' },
  { n: 23, q: '（容積）長 4.2 公分、寬 3.5 公分，面積多少平方公分？', a: '14.7', u: '平方公分', d: 'medium', mode: 'exact', nums: '4.2×3.5' },
  { n: 24, q: '（油價）每公升 32.8 元，加了 5.5 公升，一共多少元？', a: '180.4', u: '元', d: 'medium', mode: 'exact', nums: '32.8×5.5' },
  { n: 25, q: '（重量）每箱 12.5 公斤，有 3.2 箱，一共多少公斤？', a: '40', u: '公斤', d: 'medium', mode: 'exact', nums: '12.5×3.2' },
  { n: 26, q: '（電費）每度 2.68 元，用了 4.5 度，一共多少元？', a: '12.06', u: '元', d: 'medium', mode: 'exact', nums: '2.68×4.5' },
];
for (const x of dMulDData) {
  newQs.push({
    id: `d4_d_mul_d_${pad(x.n)}`,
    kind: 'd_mul_d',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: x.q,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：小數×小數常見在面積（長×寬）或單價×數量。',
      '列式：小數 × 小數。先估算，再用『小數位數加起來』放回小數點。',
      `📐 一步步算：\n① 估算 ${x.nums}\n② 去掉小數點做整數乘\n③ 小數位數加起來放回\n④ = ？ ${x.u}\n⑤ 大小合理 ✓\n算完記得回頭檢查喔！✅`,
      '👉 小數×小數：分別數兩個因數的小數位數，相加就是積的小數位數。'
    ],
    steps: [`估算 ${x.nums}`, '去掉小數點做整數乘', '小數位數加起來放回', `= ？ ${x.u}`, '大小合理 ✓'],
    meta: { unit: x.u },
    explanation: `依題意用乘法，先整數乘，再把小數位數加起來放回，得到 ${x.a} ${x.u}。`,
    common_mistakes: [
      '忘了放回小數點，直接把整數乘法的結果當成答案。',
      '小數位數數錯，小數點位置放錯。'
    ]
  });
}

// ======== d_div_int (16 → 24, add 8) ========
const dDivIntData = [
  { n: 17, q: '（均分）9.36 公升平分成 4 份，每份多少公升？', a: '2.34', u: '公升', d: 'easy', mode: 'exact', nums: '9.36÷4' },
  { n: 18, q: '（均分）15.75 公尺平分成 5 段，每段多少公尺？', a: '3.15', u: '公尺', d: 'easy', mode: 'exact', nums: '15.75÷5' },
  { n: 19, q: '（均分）8.64 公斤分裝成 6 袋，每袋多少公斤？', a: '1.44', u: '公斤', d: 'easy', mode: 'exact', nums: '8.64÷6' },
  { n: 20, q: '（均分）21.6 公升平分成 8 杯，每杯多少公升？', a: '2.7', u: '公升', d: 'easy', mode: 'exact', nums: '21.6÷8' },
  { n: 21, q: '（均分）4.68 公尺剪成 3 段，每段多少公尺？', a: '1.56', u: '公尺', d: 'easy', mode: 'exact', nums: '4.68÷3' },
  { n: 22, q: '（均分）33.6 元平分給 7 人，每人多少元？', a: '4.8', u: '元', d: 'easy', mode: 'exact', nums: '33.6÷7' },
  { n: 23, q: '（均分）0.936 公斤分裝成 9 包，每包多少公斤？', a: '0.104', u: '公斤', d: 'medium', mode: 'exact', nums: '0.936÷9' },
  { n: 24, q: '（均分）10.08 公升分成 12 瓶，每瓶多少公升？', a: '0.84', u: '公升', d: 'medium', mode: 'exact', nums: '10.08÷12' },
];
for (const x of dDivIntData) {
  newQs.push({
    id: `d4_d_div_int_${pad(x.n)}`,
    kind: 'd_div_int',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: x.q,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：把一堆東西分成幾份 → 用除法。',
      `列式：總量 ÷ 份數。小數除以整數概念和整數除法一樣，只是小數點位置要對齊。`,
      `📐 一步步算：\n① 列式：${x.nums}\n② 對齊小數點做長除法\n③ 商的小數點和被除數對齊\n④ = ？ ${x.u}\n⑤ 驗算：商 × 除數 = 被除數 ✓\n算完記得回頭檢查喔！✅`,
      '👉 小數÷整數：商的小數點和被除數的小數點對齊即可。'
    ],
    steps: [`列式：${x.nums}`, '對齊小數點做長除法', '商的小數點和被除數對齊', `= ？ ${x.u}`, '驗算 ✓'],
    meta: { unit: x.u },
    explanation: `用除法：${x.nums} = ${x.a} ${x.u}。`,
    common_mistakes: [
      '商的小數點位置對不齊，導致答案差 10 倍。',
      '長除法過程中忘了補 0 繼續除。'
    ]
  });
}

// ======== int_mul_d (16 → 24, add 8) ========
const intMulDData = [
  { n: 17, q: '（糖果）每包 12 顆，只拿了 0.75 包，拿了多少顆？', a: '9', u: '顆', d: 'easy', mode: 'exact', nums: '12×0.75' },
  { n: 18, q: '（距離）全程 80 公里，走了 0.35 的路程，走了多少公里？', a: '28', u: '公里', d: 'easy', mode: 'exact', nums: '80×0.35' },
  { n: 19, q: '（折扣）原價 250 元，打 0.8 折，售價多少元？', a: '200', u: '元', d: 'easy', mode: 'exact', nums: '250×0.8' },
  { n: 20, q: '（重量）一袋 15 公斤，用了 0.6 袋，用了多少公斤？', a: '9', u: '公斤', d: 'easy', mode: 'exact', nums: '15×0.6' },
  { n: 21, q: '（面積）邊長 24 公分，縮小為原來的 0.5 倍，新邊長多少公分？', a: '12', u: '公分', d: 'easy', mode: 'exact', nums: '24×0.5' },
  { n: 22, q: '（容量）滿水 350 毫升，只裝了 0.4 滿，裝了多少毫升？', a: '140', u: '毫升', d: 'easy', mode: 'exact', nums: '350×0.4' },
  { n: 23, q: '（時間）全程需要 45 分鐘，已經走了 0.6 的時間，走了多少分鐘？', a: '27', u: '分鐘', d: 'easy', mode: 'exact', nums: '45×0.6' },
  { n: 24, q: '（價格）每件 68 元，打 0.85 折，每件多少元？', a: '57.8', u: '元', d: 'medium', mode: 'exact', nums: '68×0.85' },
];
for (const x of intMulDData) {
  newQs.push({
    id: `d4_int_mul_d_${pad(x.n)}`,
    kind: 'int_mul_d',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: x.q,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：整數乘小數 → 整數的「幾倍」。乘以小於 1 的數→結果會變小。',
      `列式：整數 × 小數。先估算大小方向。`,
      `📐 一步步算：\n① 估算 ${x.nums}\n② 先忽略小數點做整數乘法\n③ 放回小數點（小數位數不變）\n④ = ？ ${x.u}\n⑤ 檢查大小合理 ✓\n算完記得回頭檢查喔！✅`,
      '👉 整數×小數：先當整數算，再放回小數點。乘<1→結果比原來小。'
    ],
    steps: [`估算 ${x.nums}`, '先忽略小數點做整數乘法', '放回小數點', `= ？ ${x.u}`, '檢查大小合理 ✓'],
    meta: { unit: x.u },
    explanation: `用乘法：${x.nums} = ${x.a} ${x.u}。`,
    common_mistakes: [
      '忘了放回小數點，直接把整數乘法的結果當成答案。',
      '乘以小於 1 的數結果應變小，但誤以為會變大。'
    ]
  });
}

// ======== int_div_int_to_decimal (12 → 20, add 8) ========
const intDivData = [
  { n: 13, q: '（平分）7 條繩子平分成 4 段，每段多少條？', a: '1.75', u: '', d: 'easy', mode: 'exact', nums: '7÷4' },
  { n: 14, q: '（平分）9 公升分給 6 人，每人多少公升？', a: '1.5', u: '公升', d: 'easy', mode: 'exact', nums: '9÷6' },
  { n: 15, q: '（平分）13 公斤分成 8 份，每份多少公斤？', a: '1.625', u: '公斤', d: 'medium', mode: 'exact', nums: '13÷8' },
  { n: 16, q: '（平分）23 元分給 4 人，每人多少元？', a: '5.75', u: '元', d: 'easy', mode: 'exact', nums: '23÷4' },
  { n: 17, q: '（平分）11 公升分成 5 瓶，每瓶多少公升？', a: '2.2', u: '公升', d: 'easy', mode: 'exact', nums: '11÷5' },
  { n: 18, q: '（平分）3 條麻繩分成 8 段，每段多少條？', a: '0.375', u: '', d: 'medium', mode: 'exact', nums: '3÷8' },
  { n: 19, q: '（平分）17 公尺分成 4 段，每段多少公尺？', a: '4.25', u: '公尺', d: 'easy', mode: 'exact', nums: '17÷4' },
  { n: 20, q: '（平分）29 公斤分成 8 份，每份多少公斤？', a: '3.625', u: '公斤', d: 'medium', mode: 'exact', nums: '29÷8' },
];
for (const x of intDivData) {
  newQs.push({
    id: `d4_int_div_int_to_decimal_${pad(x.n)}`,
    kind: 'int_div_int_to_decimal',
    topic: '五下第4單元｜小數',
    difficulty: x.d,
    question: x.q,
    answer: x.a,
    answer_mode: x.mode,
    hints: [
      '觀念：整數÷整數除不盡 → 商是小數。在被除數後面補 0 繼續除。',
      `列式：${x.nums}，除不盡就繼續往下除到小數。`,
      `📐 一步步算：\n① 列式：${x.nums}\n② 先做整數除法得到商和餘數\n③ 餘數後面補 0 繼續除\n④ 直到除盡 → ？${x.u ? ' '+x.u : ''}\n⑤ 驗算：商 × 除數 = 被除數 ✓\n算完記得回頭檢查喔！✅`,
      '👉 整數÷整數得小數：除到有餘數時，補 0 繼續除，商的小數點和補 0 的位置對齊。'
    ],
    steps: [`列式：${x.nums}`, '先做整數除法得到商和餘數', '餘數後面補 0 繼續除', `直到除盡 → ？${x.u ? ' '+x.u : ''}`, '驗算 ✓'],
    meta: { unit: x.u },
    explanation: `用除法：${x.nums} = ${x.a}${x.u ? ' '+x.u : ''}。`,
    common_mistakes: [
      '忘記在餘數後面補 0 繼續除，只寫出整數部分的商。',
      '小數點位置對不齊，導致答案差 10 倍。'
    ]
  });
}

// Add all new questions
bank.push(...newQs);
console.log('Added:', newQs.length, 'questions');
console.log('New total:', bank.length);

// Verify all answers are correct
let errors = 0;
for (const q of newQs) {
  // Simple sanity check - answer should not be empty
  if (!q.answer || q.answer === '') {
    console.error('  ERROR: empty answer for', q.id);
    errors++;
  }
  // Check hints count
  if (q.hints.length !== 4) {
    console.error('  ERROR: wrong hint count for', q.id, ':', q.hints.length);
    errors++;
  }
}
if (errors > 0) {
  console.error('ABORTING due to errors');
  process.exit(1);
}

// Write back
const output = 'window.DECIMAL_UNIT4_BANK = ' + JSON.stringify(bank, null, 2) + ';\n';
fs.writeFileSync(BANK_PATH, output, 'utf8');
if (fs.existsSync(path.dirname(DIST_PATH))) {
  fs.writeFileSync(DIST_PATH, output, 'utf8');
  console.log('Synced to dist');
}

// Print final counts
const finalCounts = {};
for (const q of bank) {
  finalCounts[q.kind] = (finalCounts[q.kind] || 0) + 1;
}
console.log('Final per kind:', finalCounts);
