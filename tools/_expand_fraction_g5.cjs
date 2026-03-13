#!/usr/bin/env node
/**
 * Expand fraction-g5 from 123 to ~180 questions.
 * Current: simplify(20), add_like(14), mixed_convert(16), sub_unlike(11),
 *          mul_int(12), mul(11), add_unlike(12), sub_like(13), equivalent(14) = 123
 * Target:  simplify(25), add_like(20), mixed_convert(22), sub_unlike(20),
 *          mul_int(20), mul(20), add_unlike(20), sub_like(20), equivalent(20) = ~187
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const BANK_PATH = path.join(__dirname, '..', 'docs', 'fraction-g5', 'bank.js');
const DIST_PATH = path.join(__dirname, '..', 'dist_ai_math_web_pages', 'docs', 'fraction-g5', 'bank.js');

const src = fs.readFileSync(BANK_PATH, 'utf8');
const ctx = { window: {} };
vm.runInNewContext(src, ctx);
const bank = ctx.window.FRACTION_G5_BANK;
console.log('Existing:', bank.length);

const pad = n => String(n).padStart(3, '0');
const TOPIC = '國小五年級｜分數（計算）';
const newQs = [];

// ======== simplify (20 → 25, add 5) ========
const simplifyData = [
  { n: 21, q: '把分數化成最簡分數：36/48', a: '3/4', d: 'easy', gcd: 12 },
  { n: 22, q: '把分數化成最簡分數：45/60', a: '3/4', d: 'easy', gcd: 15 },
  { n: 23, q: '把分數化成最簡分數：28/42', a: '2/3', d: 'medium', gcd: 14 },
  { n: 24, q: '把分數化成最簡分數：35/56', a: '5/8', d: 'medium', gcd: 7 },
  { n: 25, q: '把分數化成最簡分數：54/72', a: '3/4', d: 'medium', gcd: 18 },
];
for (const x of simplifyData) {
  const parts = x.q.match(/(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_simplify_${pad(x.n)}`, kind: 'simplify', topic: TOPIC, difficulty: x.d,
    question: `（約分）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n約分 = 找到分子和分母的「最大公因數」後，同時除以它。結果是最簡分數。',
      '做法：先找分子分母的公因數（先試 2、3、5…），能一直除就一直除到不能再除。',
      `📐 一步步算：\n① gcd(${parts[1]},${parts[2]}) = ${x.gcd}\n② 分子分母同除以 ${x.gcd}\n③ = ？\n算完記得回頭檢查喔！✅`,
      '👉 約分：找到分子和分母的最大公因數(GCD)，然後分子分母同時除以 GCD。結果就是最簡分數。'
    ],
    steps: [`gcd(${parts[1]},${parts[2]}) = ${x.gcd}`, `分子分母同除以 ${x.gcd}`, `= ${x.a}`],
    explanation: `${parts[1]}/${parts[2]} 的最簡分數是 ${x.a}。`,
    common_mistakes: [
      `只約了一部分而不是最大公因數 ${x.gcd}，還可以繼續約。`,
      '分子分母除以不同的數，比例改變了。'
    ]
  });
}

// ======== add_like (14 → 20, add 6) ========
const addLikeData = [
  { n: 15, q: '計算：3/11 + 5/11 = ?', a: '8/11', d: 'easy' },
  { n: 16, q: '計算：7/15 + 4/15 = ?', a: '11/15', d: 'easy' },
  { n: 17, q: '計算：2/9 + 5/9 = ?', a: '7/9', d: 'easy' },
  { n: 18, q: '計算：5/12 + 1/12 = ?', a: '1/2', d: 'easy' },
  { n: 19, q: '計算：8/21 + 6/21 = ?', a: '2/3', d: 'medium' },
  { n: 20, q: '計算：3/16 + 5/16 = ?', a: '1/2', d: 'easy' },
];
for (const x of addLikeData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*\+\s*(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_add_like_${pad(x.n)}`, kind: 'add_like', topic: TOPIC, difficulty: x.d,
    question: `（同分母加法）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n同分母分數加法：分母不變，分子相加。',
      `做法：${m[1]}/${m[2]} + ${m[3]}/${m[4]} → 分母都是 ${m[2]}，分子 ${m[1]}+${m[3]} = ${parseInt(m[1])+parseInt(m[3])}。`,
      `📐 一步步算：\n① 分母相同 = ${m[2]}\n② 分子 ${m[1]}+${m[3]} = ${parseInt(m[1])+parseInt(m[3])}\n③ 結果 = ${parseInt(m[1])+parseInt(m[3])}/${m[2]}\n④ 如需約分 → ？\n算完記得回頭檢查喔！✅`,
      '👉 同分母加法：分母不動、分子加起來，最後約分成最簡分數。'
    ],
    steps: [`分母相同 = ${m[2]}`, `分子 ${m[1]}+${m[3]} = ${parseInt(m[1])+parseInt(m[3])}`, '如需約分', `= ${x.a}`],
    explanation: `${m[1]}/${m[2]} + ${m[3]}/${m[4]} = ${parseInt(m[1])+parseInt(m[3])}/${m[2]}，約分後 = ${x.a}。`,
    common_mistakes: [
      '分母也相加了（變成兩倍大），分母應該不變。',
      '忘記約分，答案不是最簡分數。'
    ]
  });
}

// ======== sub_like (13 → 20, add 7) ========
const subLikeData = [
  { n: 15, q: '計算：9/11 - 4/11 = ?', a: '5/11', d: 'easy' },
  { n: 16, q: '計算：11/15 - 4/15 = ?', a: '7/15', d: 'easy' },
  { n: 17, q: '計算：7/8 - 3/8 = ?', a: '1/2', d: 'easy' },
  { n: 18, q: '計算：13/18 - 7/18 = ?', a: '1/3', d: 'medium' },
  { n: 19, q: '計算：5/6 - 1/6 = ?', a: '2/3', d: 'easy' },
  { n: 20, q: '計算：10/21 - 3/21 = ?', a: '1/3', d: 'medium' },
  { n: 21, q: '計算：7/12 - 1/12 = ?', a: '1/2', d: 'easy' },
];
for (const x of subLikeData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*-\s*(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_sub_like_${pad(x.n)}`, kind: 'sub_like', topic: TOPIC, difficulty: x.d,
    question: `（同分母減法）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n同分母分數減法：分母不變，分子相減。',
      `做法：${m[1]}/${m[2]} - ${m[3]}/${m[4]} → 分母都是 ${m[2]}，分子 ${m[1]}-${m[3]} = ${parseInt(m[1])-parseInt(m[3])}。`,
      `📐 一步步算：\n① 分母相同 = ${m[2]}\n② 分子 ${m[1]}-${m[3]} = ${parseInt(m[1])-parseInt(m[3])}\n③ 結果 = ${parseInt(m[1])-parseInt(m[3])}/${m[2]}\n④ 如需約分 → ？\n算完記得回頭檢查喔！✅`,
      '👉 同分母減法：分母不動、分子相減，最後約分成最簡分數。'
    ],
    steps: [`分母相同 = ${m[2]}`, `分子 ${m[1]}-${m[3]} = ${parseInt(m[1])-parseInt(m[3])}`, '如需約分', `= ${x.a}`],
    explanation: `${m[1]}/${m[2]} - ${m[3]}/${m[4]} = ${parseInt(m[1])-parseInt(m[3])}/${m[2]}，約分後 = ${x.a}。`,
    common_mistakes: [
      '分母也相減了，分母應該不變。',
      '忘記約分，答案不是最簡分數。'
    ]
  });
}

// ======== add_unlike (12 → 20, add 8) ========
const addUnlikeData = [
  { n: 13, q: '計算：1/3 + 1/6 = ?', a: '1/2', d: 'easy', lcd: 6, n1: 2, n2: 1 },
  { n: 14, q: '計算：2/5 + 1/4 = ?', a: '13/20', d: 'medium', lcd: 20, n1: 8, n2: 5 },
  { n: 15, q: '計算：3/8 + 1/6 = ?', a: '13/24', d: 'medium', lcd: 24, n1: 9, n2: 4 },
  { n: 16, q: '計算：1/4 + 2/3 = ?', a: '11/12', d: 'easy', lcd: 12, n1: 3, n2: 8 },
  { n: 17, q: '計算：3/10 + 2/5 = ?', a: '7/10', d: 'easy', lcd: 10, n1: 3, n2: 4 },
  { n: 18, q: '計算：1/6 + 3/8 = ?', a: '13/24', d: 'medium', lcd: 24, n1: 4, n2: 9 },
  { n: 19, q: '計算：2/9 + 1/3 = ?', a: '5/9', d: 'easy', lcd: 9, n1: 2, n2: 3 },
  { n: 20, q: '計算：5/12 + 1/4 = ?', a: '2/3', d: 'easy', lcd: 12, n1: 5, n2: 3 },
];
for (const x of addUnlikeData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*\+\s*(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_add_unlike_${pad(x.n)}`, kind: 'add_unlike', topic: TOPIC, difficulty: x.d,
    question: `（異分母加法）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n異分母加法：先通分（找公倍數做分母），再分子相加。',
      `做法：${m[1]}/${m[2]} 和 ${m[3]}/${m[4]} 的最小公倍數是 ${x.lcd}，通分後再加。`,
      `📐 一步步算：\n① LCM(${m[2]},${m[4]}) = ${x.lcd}\n② 通分：${x.n1}/${x.lcd} + ${x.n2}/${x.lcd}\n③ 分子 ${x.n1}+${x.n2} = ${x.n1+x.n2}\n④ 如需約分 → ？\n算完記得回頭檢查喔！✅`,
      '👉 異分母：先找分母的最小公倍數(LCM)通分，再分子相加，最後約分。'
    ],
    steps: [`LCM(${m[2]},${m[4]}) = ${x.lcd}`, `通分：${x.n1}/${x.lcd} + ${x.n2}/${x.lcd}`, `分子 ${x.n1}+${x.n2} = ${x.n1+x.n2}`, `= ${x.a}`],
    explanation: `先通分到 ${x.lcd}：${x.n1}/${x.lcd} + ${x.n2}/${x.lcd} = ${x.n1+x.n2}/${x.lcd}，約分後 = ${x.a}。`,
    common_mistakes: [
      '沒有通分就直接加，分母不同不能直接加分子。',
      '通分時只改了分母沒改分子，忘了乘以倍數。'
    ]
  });
}

// ======== sub_unlike (11 → 20, add 9) ========
const subUnlikeData = [
  { n: 13, q: '計算：5/6 - 1/3 = ?', a: '1/2', d: 'easy', lcd: 6, n1: 5, n2: 2 },
  { n: 14, q: '計算：3/4 - 1/6 = ?', a: '7/12', d: 'medium', lcd: 12, n1: 9, n2: 2 },
  { n: 15, q: '計算：7/10 - 1/4 = ?', a: '9/20', d: 'medium', lcd: 20, n1: 14, n2: 5 },
  { n: 16, q: '計算：2/3 - 1/4 = ?', a: '5/12', d: 'easy', lcd: 12, n1: 8, n2: 3 },
  { n: 17, q: '計算：5/8 - 1/3 = ?', a: '7/24', d: 'medium', lcd: 24, n1: 15, n2: 8 },
  { n: 18, q: '計算：7/9 - 1/3 = ?', a: '4/9', d: 'easy', lcd: 9, n1: 7, n2: 3 },
  { n: 19, q: '計算：4/5 - 3/10 = ?', a: '1/2', d: 'easy', lcd: 10, n1: 8, n2: 3 },
  { n: 20, q: '計算：5/6 - 1/4 = ?', a: '7/12', d: 'medium', lcd: 12, n1: 10, n2: 3 },
  { n: 21, q: '計算：3/5 - 1/4 = ?', a: '7/20', d: 'medium', lcd: 20, n1: 12, n2: 5 },
];
for (const x of subUnlikeData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*-\s*(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_sub_unlike_${pad(x.n)}`, kind: 'sub_unlike', topic: TOPIC, difficulty: x.d,
    question: `（異分母減法）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n異分母減法：先通分（找公倍數做分母），再分子相減。',
      `做法：${m[1]}/${m[2]} 和 ${m[3]}/${m[4]} 的最小公倍數是 ${x.lcd}，通分後再減。`,
      `📐 一步步算：\n① LCM(${m[2]},${m[4]}) = ${x.lcd}\n② 通分：${x.n1}/${x.lcd} - ${x.n2}/${x.lcd}\n③ 分子 ${x.n1}-${x.n2} = ${x.n1-x.n2}\n④ 如需約分 → ？\n算完記得回頭檢查喔！✅`,
      '👉 異分母：先找分母的最小公倍數(LCM)通分，再分子相減，最後約分。'
    ],
    steps: [`LCM(${m[2]},${m[4]}) = ${x.lcd}`, `通分：${x.n1}/${x.lcd} - ${x.n2}/${x.lcd}`, `分子 ${x.n1}-${x.n2} = ${x.n1-x.n2}`, `= ${x.a}`],
    explanation: `先通分到 ${x.lcd}：${x.n1}/${x.lcd} - ${x.n2}/${x.lcd} = ${x.n1-x.n2}/${x.lcd}，約分後 = ${x.a}。`,
    common_mistakes: [
      '沒有通分就直接減，分母不同不能直接減分子。',
      '通分時只改了分母沒改分子，忘了乘以倍數。'
    ]
  });
}

// ======== mixed_convert (16 → 22, add 6) ========
const mixedData = [
  { n: 17, q: '把假分數化成帶分數：23/5', a: '4又3/5', d: 'easy' },
  { n: 18, q: '把帶分數化成假分數：3又2/7', a: '23/7', d: 'easy' },
  { n: 19, q: '把假分數化成帶分數：37/8', a: '4又5/8', d: 'medium' },
  { n: 20, q: '把帶分數化成假分數：5又1/3', a: '16/3', d: 'easy' },
  { n: 21, q: '把假分數化成帶分數：19/4', a: '4又3/4', d: 'easy' },
  { n: 22, q: '把帶分數化成假分數：2又5/9', a: '23/9', d: 'easy' },
];
for (const x of mixedData) {
  const toMixed = x.q.includes('假分數化成帶分數');
  if (toMixed) {
    const m = x.q.match(/(\d+)\/(\d+)/);
    const whole = Math.floor(parseInt(m[1]) / parseInt(m[2]));
    const rem = parseInt(m[1]) % parseInt(m[2]);
    newQs.push({
      id: `fg5_mixed_convert_${pad(x.n)}`, kind: 'mixed_convert', topic: TOPIC, difficulty: x.d,
      question: `（假帶互換）${x.q}`,
      answer: x.a,
      hints: [
        '⭐ 觀念提醒\n假分數化帶分數：用分子÷分母，商=整數部分，餘數=新分子。',
        `做法：${m[1]} ÷ ${m[2]} = 商 ${whole} 餘 ${rem}，所以是 ${whole}又${rem}/${m[2]}。`,
        `📐 一步步算：\n① ${m[1]} ÷ ${m[2]} = ？ ... ？\n② 商 = 整數部分\n③ 餘數 = 新分子\n④ = ？又？/${m[2]}\n算完記得回頭檢查喔！✅`,
        '👉 假→帶：分子÷分母，商是整數、餘數放分子上、分母不變。'
      ],
      steps: [`${m[1]} ÷ ${m[2]}`, `= ${whole} ... ${rem}`, `= ${x.a}`],
      explanation: `${m[1]}/${m[2]} = ${whole}又${rem}/${m[2]} = ${x.a}。`,
      common_mistakes: [
        '商和餘數搞反，把餘數當整數部分。',
        '忘記分母要保持不變。'
      ]
    });
  } else {
    const m = x.q.match(/(\d+)又(\d+)\/(\d+)/);
    const num = parseInt(m[1]) * parseInt(m[3]) + parseInt(m[2]);
    newQs.push({
      id: `fg5_mixed_convert_${pad(x.n)}`, kind: 'mixed_convert', topic: TOPIC, difficulty: x.d,
      question: `（假帶互換）${x.q}`,
      answer: x.a,
      hints: [
        '⭐ 觀念提醒\n帶分數化假分數：整數×分母+分子 = 新分子，分母不變。',
        `做法：${m[1]} × ${m[3]} + ${m[2]} = ${num}，所以是 ${num}/${m[3]}。`,
        `📐 一步步算：\n① 整數 × 分母 = ${m[1]} × ${m[3]} = ${parseInt(m[1])*parseInt(m[3])}\n② 再加分子 + ${m[2]} = ${num}\n③ = ${num}/${m[3]}\n算完記得回頭檢查喔！✅`,
        '👉 帶→假：整數×分母+分子，放在分母上面，分母不變。'
      ],
      steps: [`${m[1]} × ${m[3]} = ${parseInt(m[1])*parseInt(m[3])}`, `+ ${m[2]} = ${num}`, `= ${num}/${m[3]}`],
      explanation: `${m[1]}又${m[2]}/${m[3]} = ${num}/${m[3]} = ${x.a}。`,
      common_mistakes: [
        '忘記加分子，只做整數×分母。',
        '分母跟著改變了，分母應該保持不變。'
      ]
    });
  }
}

// ======== mul_int (12 → 20, add 8) ========
const mulIntData = [
  { n: 13, q: '計算：3/7 × 5 = ?', a: '2又1/7', d: 'easy', frac: '3/7', int: 5 },
  { n: 14, q: '計算：4/9 × 6 = ?', a: '2又2/3', d: 'medium', frac: '4/9', int: 6 },
  { n: 15, q: '計算：5/8 × 4 = ?', a: '2又1/2', d: 'easy', frac: '5/8', int: 4 },
  { n: 16, q: '計算：2/11 × 3 = ?', a: '6/11', d: 'easy', frac: '2/11', int: 3 },
  { n: 17, q: '計算：7/12 × 8 = ?', a: '4又2/3', d: 'medium', frac: '7/12', int: 8 },
  { n: 18, q: '計算：3/10 × 5 = ?', a: '3/2', d: 'easy', frac: '3/10', int: 5 },
  { n: 19, q: '計算：5/6 × 3 = ?', a: '2又1/2', d: 'easy', frac: '5/6', int: 3 },
  { n: 20, q: '計算：4/15 × 9 = ?', a: '2又2/5', d: 'medium', frac: '4/15', int: 9 },
];
for (const x of mulIntData) {
  const m = x.frac.match(/(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_mul_int_${pad(x.n)}`, kind: 'mul_int', topic: TOPIC, difficulty: x.d,
    question: `（分數×整數）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n分數×整數 = 分子×整數，分母不變。',
      `做法：${m[1]}/${m[2]} × ${x.int} → 分子 ${m[1]}×${x.int} = ${parseInt(m[1])*x.int}，分母 ${m[2]} 不變。`,
      `📐 一步步算：\n① 分子 ${m[1]} × ${x.int} = ${parseInt(m[1])*x.int}\n② = ${parseInt(m[1])*x.int}/${m[2]}\n③ 約分或化成帶分數 → ？\n算完記得回頭檢查喔！✅`,
      '👉 分數×整數：整數乘分子，分母不動，最後約分或化帶分數。'
    ],
    steps: [`分子 ${m[1]} × ${x.int} = ${parseInt(m[1])*x.int}`, `= ${parseInt(m[1])*x.int}/${m[2]}`, `約分/化帶分數 = ${x.a}`],
    explanation: `${m[1]}/${m[2]} × ${x.int} = ${parseInt(m[1])*x.int}/${m[2]} = ${x.a}。`,
    common_mistakes: [
      '分母也乘了整數，應該只有分子乘整數。',
      '忘記約分或化帶分數。'
    ]
  });
}

// ======== mul (11 → 20, add 9) ========
const mulData = [
  { n: 13, q: '計算：2/5 × 3/7 = ?', a: '6/35', d: 'easy' },
  { n: 14, q: '計算：4/9 × 3/8 = ?', a: '1/6', d: 'medium' },
  { n: 15, q: '計算：5/6 × 2/5 = ?', a: '1/3', d: 'easy' },
  { n: 16, q: '計算：3/4 × 2/9 = ?', a: '1/6', d: 'easy' },
  { n: 17, q: '計算：7/10 × 5/14 = ?', a: '1/4', d: 'medium' },
  { n: 18, q: '計算：4/7 × 7/12 = ?', a: '1/3', d: 'medium' },
  { n: 19, q: '計算：2/3 × 5/8 = ?', a: '5/12', d: 'easy' },
  { n: 20, q: '計算：3/8 × 4/5 = ?', a: '3/10', d: 'easy' },
  { n: 21, q: '計算：5/9 × 3/10 = ?', a: '1/6', d: 'medium' },
];
for (const x of mulData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*×\s*(\d+)\/(\d+)/);
  newQs.push({
    id: `fg5_mul_${pad(x.n)}`, kind: 'mul', topic: TOPIC, difficulty: x.d,
    question: `（分數乘法）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n分數×分數 = 分子×分子，分母×分母。記得先約分再乘更簡單。',
      `做法：${m[1]}/${m[2]} × ${m[3]}/${m[4]}，先看能不能交叉約分，再分子乘分子、分母乘分母。`,
      `📐 一步步算：\n① 看看能不能先約分（對角線找公因數）\n② 分子相乘、分母相乘\n③ 化成最簡分數 → ？\n算完記得回頭檢查喔！✅`,
      '👉 分數×分數：先交叉約分（上下對角找公因數），再分子乘分子、分母乘分母。'
    ],
    steps: ['檢查能否先約分', '分子乘分子、分母乘分母', `= ${x.a}`],
    explanation: `${m[1]}/${m[2]} × ${m[3]}/${m[4]} = ${x.a}。`,
    common_mistakes: [
      '忘記先約分，算出很大的數再約很困難。',
      '把乘法做成加法（分子加分子），分數乘法是分子乘分子。'
    ]
  });
}

// ======== equivalent (14 → 20, add 6) ========
const equivData = [
  { n: 17, q: '找出等值分數：2/5 = ?/15', a: '6/15', d: 'easy', mult: 3 },
  { n: 18, q: '找出等值分數：3/7 = ?/21', a: '9/21', d: 'easy', mult: 3 },
  { n: 19, q: '找出等值分數：4/9 = ?/36', a: '16/36', d: 'medium', mult: 4 },
  { n: 20, q: '找出等值分數：5/8 = ?/24', a: '15/24', d: 'easy', mult: 3 },
  { n: 21, q: '找出等值分數：3/4 = ?/20', a: '15/20', d: 'easy', mult: 5 },
  { n: 22, q: '找出等值分數：2/3 = ?/18', a: '12/18', d: 'easy', mult: 6 },
];
for (const x of equivData) {
  const m = x.q.match(/(\d+)\/(\d+)\s*=\s*\?\s*\/\s*(\d+)/);
  const newNum = parseInt(m[1]) * x.mult;
  newQs.push({
    id: `fg5_equivalent_${pad(x.n)}`, kind: 'equivalent', topic: TOPIC, difficulty: x.d,
    question: `（等值分數）${x.q}`,
    answer: x.a,
    hints: [
      '⭐ 觀念提醒\n等值分數：分子和分母同時乘以（或除以）相同的數，分數大小不變。',
      `做法：${m[2]} × ？ = ${m[3]}，所以乘以 ${x.mult}。分子也要乘以 ${x.mult}。`,
      `📐 一步步算：\n① ${m[3]} ÷ ${m[2]} = ${x.mult}\n② 分子 ${m[1]} × ${x.mult} = ${newNum}\n③ = ${newNum}/${m[3]}\n算完記得回頭檢查喔！✅`,
      '👉 等值分數：先算分母擴大幾倍，分子也要乘以相同倍數。'
    ],
    steps: [`${m[3]} ÷ ${m[2]} = ${x.mult}`, `分子 ${m[1]} × ${x.mult} = ${newNum}`, `= ${newNum}/${m[3]}`],
    explanation: `${m[1]}/${m[2]} = ${newNum}/${m[3]}，分子分母同乘 ${x.mult}。`,
    common_mistakes: [
      '只改分母沒改分子，分數值就變了。',
      '乘錯倍數，沒有正確算出分母的倍率。'
    ]
  });
}

// Append and write
bank.push(...newQs);
console.log('Added:', newQs.length);
console.log('New total:', bank.length);

// Sanity check
let err = 0;
for (const q of newQs) {
  if (!q.answer) { console.error('empty answer:', q.id); err++; }
  if (q.hints.length !== 4) { console.error('bad hints:', q.id, q.hints.length); err++; }
}
if (err) { console.error('ABORT'); process.exit(1); }

const out = 'window.FRACTION_G5_BANK = ' + JSON.stringify(bank, null, 2) + ';\n';
fs.writeFileSync(BANK_PATH, out, 'utf8');
if (fs.existsSync(path.dirname(DIST_PATH))) {
  fs.writeFileSync(DIST_PATH, out, 'utf8');
  console.log('Synced to dist');
}

const fc = {};
for (const q of bank) fc[q.kind] = (fc[q.kind] || 0) + 1;
console.log('Final per kind:', fc);
