(function(){
  'use strict';

  function gcd(a, b){
    a = Math.abs(a);
    b = Math.abs(b);
    while (b) {
      var tmp = a % b;
      a = b;
      b = tmp;
    }
    return a || 1;
  }

  function frac(numerator, denominator){
    var factor = gcd(numerator, denominator);
    return { n: numerator / factor, d: denominator / factor };
  }

  function fracText(numerator, denominator){
    return numerator + '/' + denominator;
  }

  function hashString(text){
    var hash = 2166136261;
    var source = String(text || '');
    for (var index = 0; index < source.length; index++) {
      hash ^= source.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function createPicker(seedText){
    var seed = hashString(seedText) || 1;
    return function(min, max){
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return min + (seed % (max - min + 1));
    };
  }

  function explainWrongDetail(w){
    var kind = String(w && w.k || '').toLowerCase();
    var mod = String(w && w.t || '').toLowerCase();
    var errType = String(w && w.et || '').toLowerCase();

    if (kind === 'generic_fraction_word' || kind === 'fraction_of_quantity') {
      return {
        cause: '分量應用題容易把對象搞混，不確定是全量的幾分之幾還是剩下的幾分之幾。',
        concept: '先找出全量，再決定是用全量乘分數，還是先求剩餘再計算。',
        tutor: '先畫線段圖標出全量與已用量，再做 3 題同結構換數字題。'
      };
    }
    if (kind === 'reverse_fraction') {
      return {
        cause: '反向分數題容易把乘除方向顛倒。',
        concept: '先找出剩下佔全部的幾分之幾，再用剩餘量反推原量。',
        tutor: '先畫出花掉與剩下的比例，再用 3 題反向題練習。'
      };
    }
    if (kind === 'cube_cm3' || kind === 'cube_find_edge' || kind === 'surface_area_cube') {
      return {
        cause: '容易把邊長、體積、表面積公式混在一起。',
        concept: '先確認題目問的是體積還是表面積，再代對公式。',
        tutor: '先口頭說公式用途，再練 3 題只改數字的正方體題。'
      };
    }
    if (kind === 'rect_cm3' || kind === 'rect_find_height' || kind === 'volume_rect_prism' || kind === 'base_area_h') {
      return {
        cause: '長方體題常把邊長對錯或忽略單位。',
        concept: '體積 = 長 × 寬 × 高，或底面積 × 高，答案要保留立方單位。',
        tutor: '先畫立體圖標三邊，再做 5 題只換一個數字的對照題。'
      };
    }
    if (mod.indexOf('fraction-word') >= 0 || mod === 'fraction-word') {
      return {
        cause: '文字題常在題意轉算式時卡住。',
        concept: '先圈關鍵詞，再拆成已知、未知、算式三步。',
        tutor: '先口述算式理由，再下筆做同類題。'
      };
    }
    if (mod.indexOf('fraction') >= 0 || kind.indexOf('fraction') >= 0) {
      return {
        cause: '分數題常在通分、約分或運算規則混用時出錯。',
        concept: '先判斷加減還是乘除，再做通分或約分。',
        tutor: '用通分格線法練 10 分鐘，再回到同類題。'
      };
    }
    if (mod.indexOf('volume') >= 0 || kind.indexOf('volume') >= 0 || kind.indexOf('cm3') >= 0) {
      return {
        cause: '空間量題常把公式或單位混掉。',
        concept: '先確認題目要的是體積、面積或邊長，再代公式。',
        tutor: '先畫圖標示量，再做 3 題對照練習。'
      };
    }
    if (errType.indexOf('careless') >= 0 || errType.indexOf('粗心') >= 0) {
      return {
        cause: '概念大致正確，但計算或抄寫時出現小錯。',
        concept: '做完後先估算量級，再做一次反向檢查。',
        tutor: '每題固定留 15 秒做符號、位值、單位檢查。'
      };
    }
    return {
      cause: '可能卡在題意理解或步驟拆解。',
      concept: '先拆成已知、未知、關係，每一步只做一個動作。',
      tutor: '先示範一題完整思路，再讓學生獨立完成兩題。'
    };
  }

  function buildPracticeOptions(w){
    return [
      { mode: 'retry', label: '直接重做', target: String(w && w.t || '這個弱點') },
      { mode: 'single', label: '類似題再練', target: String(w && w.t || '這個弱點') },
      { mode: 'quiz', label: '三題小測', target: String(w && w.t || '這個弱點') }
    ];
  }

  function buildRetryPractice(w){
    var detail = explainWrongDetail(w);
    return {
      q: String(w && w.q || '請重做這一題'),
      answer: String(w && w.ca || ''),
      hint: detail.concept
    };
  }

  function buildPracticeFromWrong(w, options){
    var mode = String(options && options.mode || 'single');
    var sequence = Number(options && options.sequence || 0) || 0;
    if (mode === 'retry') return buildRetryPractice(w);

    var kind = String(w && w.k || '').toLowerCase();
    var mod = String(w && w.t || '').toLowerCase();
    var pick = createPicker([mod, kind, String(w && w.q || ''), String(w && w.ca || ''), mode, sequence].join('|'));
    function randInt(min, max){ return pick(min, max); }

    if (kind === 'generic_fraction_word' || kind === 'fraction_of_quantity') {
      var items = ['水桶容量', '繩子長', '米缸裝了', '果汁共有'];
      var units = ['公升', '公分', '公斤', '毫升'];
      var index = randInt(0, items.length - 1);
      var den1 = [2, 3, 4, 5, 6][randInt(0, 4)];
      var num1 = randInt(1, den1 - 1);
      var total = den1 * randInt(2, 10);
      var remain = total - total * num1 / den1;
      var reduced = frac(num1, den1);
      return {
        q: items[index] + ' ' + total + ' ' + units[index] + '，已用了 ' + fracText(reduced.n, reduced.d) + '，還剩多少' + units[index] + '？',
        answer: String(remain),
        hint: '先算已用量 = 全量 × ' + fracText(reduced.n, reduced.d) + '，再用全量減去已用量。'
      };
    }

    if (kind === 'reverse_fraction') {
      var reverseDen = [3, 4, 5, 6, 8][randInt(0, 4)];
      var reverseNum = randInt(1, reverseDen - 1);
      var originalAmount = reverseDen * randInt(2, 10);
      var leftover = originalAmount - originalAmount * reverseNum / reverseDen;
      var remainFraction = frac(reverseDen - reverseNum, reverseDen);
      return {
        q: '小明花掉零用錢的 ' + fracText(reverseNum, reverseDen) + '，還剩 ' + leftover + ' 元，原來有多少元？',
        answer: String(originalAmount),
        hint: '剩下佔全部的 ' + fracText(remainFraction.n, remainFraction.d) + '，所以原來 = 剩餘 ÷ 剩餘比例。'
      };
    }

    if (kind === 'cube_cm3') {
      var edge = randInt(2, 12);
      return {
        q: '邊長 ' + edge + ' 公分的正方體，體積是多少立方公分？',
        answer: String(edge * edge * edge),
        hint: '正方體體積 = 邊長 × 邊長 × 邊長。'
      };
    }

    if (kind === 'rect_cm3' || kind === 'volume_rect_prism' || kind === 'volume_calculation') {
      var length = randInt(2, 12);
      var width = randInt(2, 10);
      var height = randInt(2, 9);
      return {
        q: '長方體長 ' + length + ' 公分、寬 ' + width + ' 公分、高 ' + height + ' 公分，體積是多少立方公分？',
        answer: String(length * width * height),
        hint: '體積 = 長 × 寬 × 高。'
      };
    }

    if (mod.indexOf('fraction-word') >= 0) {
      var den = randInt(4, 10);
      var left = randInt(1, den - 1);
      var right = randInt(1, den - left);
      var totalFraction = frac(left + right, den);
      return {
        q: '小明吃了 ' + fracText(left, den) + ' 個披薩，小華又吃了 ' + fracText(right, den) + ' 個，兩人共吃了多少個披薩？',
        answer: fracText(totalFraction.n, totalFraction.d),
        hint: '同分母分數相加，分子相加、分母不變，最後約分。'
      };
    }

    if (mod.indexOf('fraction') >= 0 || kind.indexOf('fraction') >= 0) {
      var denA = randInt(2, 9);
      var denB = randInt(2, 9);
      var numA = randInt(1, denA - 1);
      var numB = randInt(1, denB - 1);
      var result = frac(numA * denB + numB * denA, denA * denB);
      return {
        q: '計算：' + fracText(numA, denA) + ' + ' + fracText(numB, denB) + ' = ?',
        answer: fracText(result.n, result.d),
        hint: '先通分，再把分子相加，最後約分。'
      };
    }

    if (mod.indexOf('volume') >= 0 || kind.indexOf('volume') >= 0 || kind.indexOf('cm3') >= 0) {
      var volumeL = randInt(2, 12);
      var volumeW = randInt(2, 10);
      var volumeH = randInt(2, 9);
      return {
        q: '長方體長 ' + volumeL + ' 公分、寬 ' + volumeW + ' 公分、高 ' + volumeH + ' 公分，體積是多少立方公分？',
        answer: String(volumeL * volumeW * volumeH),
        hint: '先找長、寬、高，再代入體積公式。'
      };
    }

    var leftNum = randInt(20, 99);
    var rightNum = randInt(10, 49);
    return {
      q: '計算：' + leftNum + ' - ' + rightNum + ' = ?',
      answer: String(leftNum - rightNum),
      hint: '先對齊位值，做完再用加法反向檢查。'
    };
  }

  window.AIMathPracticeFromWrongEngine = {
    buildPracticeFromWrong: buildPracticeFromWrong,
    buildPracticeOptions: buildPracticeOptions,
    explainWrongDetail: explainWrongDetail
  };
})();
