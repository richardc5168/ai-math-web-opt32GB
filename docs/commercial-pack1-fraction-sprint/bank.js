// 商用試賣內容包題庫（MVP）：小五分數應用題 10 單元 × 20 題 = 200 題
// 供頁面以 window.COMMERCIAL_PACK1_FRACTION_SPRINT_BANK 讀取。

(function () {
  const PACK_ID = 'commercial.pack1.g5.fraction_sprint.tw.v1';

  function gcd(a, b) {
    a = Math.abs(a);
    b = Math.abs(b);
    while (b !== 0) {
      const t = a % b;
      a = b;
      b = t;
    }
    return a || 1;
  }

  function simp(n, d) {
    if (d < 0) { d = -d; n = -n; }
    const g = gcd(n, d);
    n = n / g;
    d = d / g;
    if (d === 1) return String(n);
    return `${n}/${d}`;
  }

  function frac(n, d) {
    const s = simp(n, d);
    const parts = s.split('/');
    if (parts.length === 1) return { n: Number(parts[0]), d: 1, s };
    return { n: Number(parts[0]), d: Number(parts[1]), s };
  }

  function mulFracInt(f, k) {
    return frac(f.n * k, f.d);
  }

  function subFrac(a, b) {
    return frac(a.n * b.d - b.n * a.d, a.d * b.d);
  }

  function choose(arr, i) {
    return arr[i % arr.length];
  }

  // Kinds: original, remain, part_to_total, compare
  const UNITS = [
    { unit_id: 'U1', title: '找原量：已知 = 原量×分數', kind: 'original' },
    { unit_id: 'U2', title: '找剩下：先算剩下比例', kind: 'remain' },
    { unit_id: 'U3', title: '找部分：部分 = 原量×分數', kind: 'part_to_total' },
    { unit_id: 'U4', title: '兩步題：先部分再剩下', kind: 'remain' },
    { unit_id: 'U5', title: '比一比：差多少', kind: 'compare' },
    { unit_id: 'U6', title: '線段圖：把總量切成幾份', kind: 'original' },
    { unit_id: 'U7', title: '單位量：每 1 份是多少', kind: 'original' },
    { unit_id: 'U8', title: '混合分數：先轉假分數', kind: 'part_to_total' },
    { unit_id: 'U9', title: '多段剩下：連續扣掉', kind: 'remain' },
    { unit_id: 'U10', title: '綜合：讀題抓基準量', kind: 'compare' }
  ];

  const NAMES = ['小明', '小華', '小芸', '阿哲', '小安'];
  const ITEMS = ['糖果', '貼紙', '彩色筆', '積木', '餅乾'];

  function makeItem({ id, unit, difficulty, question, answer, hints, steps }) {
    return {
      id,
      pack_id: PACK_ID,
      kind: unit.kind,
      unit_id: unit.unit_id,
      difficulty,
      question,
      answer,
      hints,
      steps
    };
  }

  function hintsOriginal(fr, knownStr) {
    return [
      '先找「基準量」：題目問的是原來有多少（總量）。',
      `列式：已知 = 原量 × ${fr.s}。所以 原量 = 已知 ÷ ${fr.s}。`,
      `把「÷ 分數」想成「× 倒數」：已知 ÷ ${fr.s} = 已知 × ${fr.d}/${fr.n}。`
    ];
  }

  function stepsOriginal(fr, known, ans) {
    return [
      `讀題：已知是原量的 ${fr.s}，已知為 ${known}。`,
      `列式：${known} = 原量 × ${fr.s}。`,
      `原量 = ${known} ÷ ${fr.s} = ${known} × ${fr.d}/${fr.n}。`,
      `計算得到原量 = ${ans}。`,
      '檢查：把原量 × 分數，是否回到已知？'
    ];
  }

  function hintsRemain(frUsed) {
    const remain = subFrac(frac(1, 1), frUsed);
    return [
      '先找「基準量」：總量是 1。',
      `用掉的是 ${frUsed.s}，剩下比例 = 1 − ${frUsed.s} = ${remain.s}。`,
      `剩下數量 = 總量 × ${remain.s}。`
    ];
  }

  function stepsRemain(total, frUsed, remainAns) {
    const remain = subFrac(frac(1, 1), frUsed);
    return [
      `總量 = ${total}。用掉比例 = ${frUsed.s}。`,
      `剩下比例 = 1 − ${frUsed.s} = ${remain.s}。`,
      `剩下 = ${total} × ${remain.s}。`,
      `計算：剩下 = ${remainAns}。`,
      '檢查：用掉 + 剩下 = 總量。'
    ];
  }

  function hintsPart(frPart) {
    return [
      '先找「基準量」：題目問的是一部分，基準量通常是「總量」。',
      `列式：部分 = 總量 × ${frPart.s}。`,
      '如果出現混合分數，先轉成假分數再算。'
    ];
  }

  function stepsPart(total, frPart, partAns) {
    return [
      `總量 = ${total}。比例 = ${frPart.s}。`,
      `部分 = ${total} × ${frPart.s}。`,
      `計算：部分 = ${partAns}。`,
      '檢查：部分 ÷ 總量 = 比例（或接近）。'
    ];
  }

  function hintsCompare() {
    return [
      '先把兩個量都表示成「同一個基準量」的分數（或都算成實際數量）。',
      '要比較差多少：用「大 − 小」。',
      '最後記得對應單位（顆/張/支…）。'
    ];
  }

  function stepsCompare(total, f1, f2, ans) {
    return [
      `總量 = ${total}。A = ${total} × ${f1.s}，B = ${total} × ${f2.s}。`,
      '先算出兩個部分各是多少。',
      `差 = |A − B| = ${ans}。`,
      '檢查：差不會超過總量。'
    ];
  }

  // Generate 200 questions
  const bank = [];
  let idCounter = 1;

  for (let u = 0; u < UNITS.length; u++) {
    const unit = UNITS[u];

    for (let i = 0; i < 20; i++) {
      const name = choose(NAMES, u * 20 + i);
      const itemName = choose(ITEMS, i + u);
      const difficulty = i < 6 ? 1 : i < 14 ? 2 : 3;

      // pick friendly fractions
      const frList = [frac(1,2), frac(1,3), frac(2,3), frac(1,4), frac(3,4), frac(2,5), frac(3,5), frac(4,5)];
      const f = choose(frList, i + u * 3);

      // choose totals that divide nicely
      const totals = [12, 15, 18, 20, 24, 30, 36, 40, 45, 48, 50, 60, 72];
      const total = choose(totals, i * 2 + u);

      let q = '';
      let ans = '';
      let hints = [];
      let steps = [];

      if (unit.kind === 'original') {
        // known part = total * f
        const knownF = mulFracInt(f, total);
        q = `${name} 有一些${itemName}。他把其中的 ${f.s} 用掉了，剛好用掉 ${knownF.s} ${itemName}。請問原來有多少${itemName}？`;
        ans = String(total);
        hints = hintsOriginal(f, knownF.s);
        steps = stepsOriginal(f, knownF.s, ans);
      } else if (unit.kind === 'remain') {
        // remain = total * (1 - f)
        const remainF = mulFracInt(subFrac(frac(1,1), f), total);
        q = `${name} 原本有 ${total} 個${itemName}。他用掉了 ${f.s} 的${itemName}，請問還剩下多少個${itemName}？`;
        ans = remainF.s;
        hints = hintsRemain(f);
        steps = stepsRemain(total, f, ans);
      } else if (unit.kind === 'part_to_total') {
        // part = total * f
        const partF = mulFracInt(f, total);
        q = `${name} 有 ${total} 個${itemName}。其中有 ${f.s} 是新的，請問新的有多少個${itemName}？`;
        ans = partF.s;
        hints = hintsPart(f);
        steps = stepsPart(total, f, ans);
      } else {
        // compare
        const f2 = choose(frList, i + u * 5 + 1);
        const a1 = mulFracInt(f, total);
        const a2 = mulFracInt(f2, total);
        const diff = frac(Math.abs(a1.n * a2.d - a2.n * a1.d), a1.d * a2.d);
        q = `${name} 有 ${total} 個${itemName}。他把其中的 ${f.s} 分給同學，另外又把 ${f2.s} 分給老師。請問分給同學和分給老師相差多少個${itemName}？`;
        ans = diff.s;
        hints = hintsCompare();
        steps = stepsCompare(total, f, f2, ans);
      }

      // Ensure hints/steps exist
      if (!Array.isArray(hints) || hints.length < 3) {
        hints = [
          '先找基準量（題目是以誰為 1）。',
          '把比例寫成算式，分清楚「乘」或「除」。',
          '最後檢查答案是否合理。'
        ];
      }
      if (!Array.isArray(steps) || steps.length < 4) {
        steps = [
          '讀題找基準量。',
          '列式。',
          '計算。',
          '檢查。'
        ];
      }

      const id = `CP1-FS-${String(idCounter).padStart(4, '0')}`;
      bank.push(makeItem({ id, unit, difficulty, question: q, answer: ans, hints, steps }));
      idCounter++;
    }
  }

  window.COMMERCIAL_PACK1_FRACTION_SPRINT_BANK = bank;
})();
