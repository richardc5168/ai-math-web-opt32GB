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

    /* Delegate to shared wrong_detail_data.js (must be loaded first) */
    var _wdd = window.AIMathWrongDetailData;
    if (_wdd && _wdd.lookup) return _wdd.lookup(kind, mod, errType);

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

    if (kind === 'original') {
      var oDen = [2, 3, 4, 5, 6][randInt(0, 4)];
      var oNum = randInt(1, oDen - 1);
      var oBase = randInt(3, 9);
      var oOriginal = oDen * oBase;
      var oPart = oOriginal * oNum / oDen;
      return {
        q: '某盒糖果的 ' + fracText(oNum, oDen) + ' 是 ' + oPart + ' 顆，原來有多少顆糖果？',
        answer: String(oOriginal),
        hint: '原量 = 部分 ÷ 對應分數。先把 ' + oPart + ' ÷ ' + fracText(oNum, oDen) + ' 改成乘倒數。'
      };
    }

    if (kind === 'remain') {
      var rDen = [3, 4, 5, 6][randInt(0, 3)];
      var rNum = randInt(1, rDen - 1);
      var rWhole = rDen * randInt(3, 8);
      var rRemain = rWhole - (rWhole * rNum / rDen);
      return {
        q: '一盒餅乾有 ' + rWhole + ' 個，吃掉 ' + fracText(rNum, rDen) + ' 後，還剩多少個？',
        answer: String(rRemain),
        hint: '先算吃掉多少，再用總數減掉吃掉的部分。'
      };
    }

    if (kind === 'part_to_total') {
      var pDen = [4, 5, 6, 8][randInt(0, 3)];
      var pNum = randInt(1, pDen - 1);
      var pTotal = pDen * randInt(2, 7);
      var pPart = pTotal * pNum / pDen;
      return {
        q: '全班有 ' + pTotal + ' 人，其中 ' + fracText(pNum, pDen) + ' 參加合唱團，參加合唱團的有幾人？',
        answer: String(pPart),
        hint: '部分 = 全量 × 分數。先求 ' + pTotal + ' × ' + fracText(pNum, pDen) + '。'
      };
    }

    if (kind === 'compare') {
      var cDen = [4, 5, 6][randInt(0, 2)];
      var cA = randInt(1, cDen - 2);
      var cB = randInt(cA + 1, cDen - 1);
      return {
        q: '比較大小：' + fracText(cA, cDen) + ' 和 ' + fracText(cB, cDen) + '，哪一個比較大？',
        answer: fracText(cB, cDen),
        hint: '同分母分數比較大小時，只要比分子。'
      };
    }

    if (kind === 'remain_multi') {
      var rmDen = [4, 5, 6][randInt(0, 2)];
      var rmUsedA = randInt(1, rmDen - 2);
      var rmUsedB = randInt(1, rmDen - rmUsedA - 1);
      var rmTotal = rmDen * randInt(3, 8);
      var rmRemain = rmTotal - (rmTotal * rmUsedA / rmDen) - (rmTotal * rmUsedB / rmDen);
      return {
        q: '一本書共有 ' + rmTotal + ' 頁，上午看了 ' + fracText(rmUsedA, rmDen) + '，下午又看了 ' + fracText(rmUsedB, rmDen) + '，還剩幾頁？',
        answer: String(rmRemain),
        hint: '先把上午和下午看的分數加起來，再求剩下的部分。'
      };
    }

    if (kind === 'add_like' || kind === 'sub_like') {
      var sameDen = [4, 5, 6, 8, 10, 12][randInt(0, 5)];
      var sameA = randInt(1, sameDen - 1);
      var sameB = randInt(1, kind === 'sub_like' ? sameA : sameDen - 1);
      var sameRes = kind === 'sub_like' ? frac(sameA - sameB, sameDen) : frac(sameA + sameB, sameDen);
      return {
        q: '計算：' + fracText(sameA, sameDen) + (kind === 'sub_like' ? ' - ' : ' + ') + fracText(sameB, sameDen) + ' = ?',
        answer: fracText(sameRes.n, sameRes.d),
        hint: '同分母分數先算分子，分母保持 ' + sameDen + ' 不變。'
      };
    }

    if (kind === 'add_unlike' || kind === 'sub_unlike') {
      var unlikePairs = [[2, 3], [2, 5], [3, 4], [4, 5], [6, 8]];
      var unlikePair = unlikePairs[randInt(0, unlikePairs.length - 1)];
      var unlikeDenA = unlikePair[0];
      var unlikeDenB = unlikePair[1];
      var unlikeNumA = randInt(1, unlikeDenA - 1);
      var unlikeNumB = randInt(1, unlikeDenB - 1);
      var unlikeLeft = frac(unlikeNumA, unlikeDenA);
      var unlikeRight = frac(unlikeNumB, unlikeDenB);
      var unlikeNum = kind === 'sub_unlike'
        ? unlikeLeft.n * unlikeRight.d - unlikeRight.n * unlikeLeft.d
        : unlikeLeft.n * unlikeRight.d + unlikeRight.n * unlikeLeft.d;
      if (kind === 'sub_unlike' && unlikeNum <= 0) {
        var unlikeTmp = unlikeLeft;
        unlikeLeft = unlikeRight;
        unlikeRight = unlikeTmp;
        unlikeNum = unlikeLeft.n * unlikeRight.d - unlikeRight.n * unlikeLeft.d;
      }
      var unlikeRes = frac(unlikeNum, unlikeLeft.d * unlikeRight.d);
      return {
        q: '計算：' + fracText(unlikeLeft.n, unlikeLeft.d) + (kind === 'sub_unlike' ? ' - ' : ' + ') + fracText(unlikeRight.n, unlikeRight.d) + ' = ?',
        answer: fracText(unlikeRes.n, unlikeRes.d),
        hint: '先找公分母，把兩個分數改成同分母後再做加減。'
      };
    }

    if (kind === 'equivalent') {
      var eqDen = [2, 3, 4, 5, 6][randInt(0, 4)];
      var eqNum = randInt(1, eqDen - 1);
      var eqMul = randInt(2, 6);
      return {
        q: '填空：' + (eqNum * eqMul) + '/□ = ' + fracText(eqNum, eqDen),
        answer: String(eqDen * eqMul),
        hint: '等值分數要分子、分母同乘相同的數。先看 ' + eqNum + ' 變成了多少倍。'
      };
    }

    if (kind === 'simplify') {
      var simpBaseDen = [2, 3, 4, 5, 6, 8][randInt(0, 5)];
      var simpBaseNum = randInt(1, simpBaseDen - 1);
      var simpMul = randInt(2, 5);
      var simpQNum = simpBaseNum * simpMul;
      var simpQDen = simpBaseDen * simpMul;
      return {
        q: '把分數化成最簡分數：' + fracText(simpQNum, simpQDen),
        answer: fracText(simpBaseNum, simpBaseDen),
        hint: '先找分子和分母都能同除的最大公因數。'
      };
    }

    if (kind === 'mixed_convert') {
      var mixDen = [2, 3, 4, 5, 6][randInt(0, 4)];
      var mixWhole = randInt(1, 4);
      var mixNum = randInt(1, mixDen - 1);
      return {
        q: '把假分數改成帶分數：' + fracText(mixWhole * mixDen + mixNum, mixDen),
        answer: mixWhole + ' ' + fracText(mixNum, mixDen),
        hint: '先用分子 ÷ 分母，商是整數部分，餘數放回分子。'
      };
    }

    if (kind === 'reciprocal') {
      var recDen = [2, 3, 4, 5, 6, 8][randInt(0, 5)];
      var recNum = randInt(1, recDen - 1);
      return {
        q: fracText(recNum, recDen) + ' 的倒數是多少？',
        answer: fracText(recDen, recNum),
        hint: '倒數就是把分子和分母交換位置。'
      };
    }

    if (kind === 'mul') {
      var mulDenA = [2, 3, 4, 5, 6][randInt(0, 4)];
      var mulDenB = [2, 3, 4, 5, 6][randInt(0, 4)];
      var mulNumA = randInt(1, mulDenA - 1);
      var mulNumB = randInt(1, mulDenB - 1);
      var mulRes = frac(mulNumA * mulNumB, mulDenA * mulDenB);
      return {
        q: '計算：' + fracText(mulNumA, mulDenA) + ' × ' + fracText(mulNumB, mulDenB) + ' = ?',
        answer: fracText(mulRes.n, mulRes.d),
        hint: '分數乘法是分子乘分子、分母乘分母，最後約分。'
      };
    }

    if (kind === 'mul_int') {
      var mulIntDen = [2, 3, 4, 5, 6, 8][randInt(0, 5)];
      var mulIntNum = randInt(1, mulIntDen - 1);
      var mulIntVal = randInt(2, 9);
      var mulIntRes = frac(mulIntNum * mulIntVal, mulIntDen);
      return {
        q: '計算：' + fracText(mulIntNum, mulIntDen) + ' × ' + mulIntVal + ' = ?',
        answer: fracText(mulIntRes.n, mulIntRes.d),
        hint: '把整數看成分母是 1 的分數，再做乘法。'
      };
    }

    if (kind === 'word_compare' || kind === '20260302test' || kind === 'national_bank_source') {
      var wcDen = [4, 5, 6, 8][randInt(0, 3)];
      var wcLeft = randInt(1, wcDen - 2);
      var wcRight = randInt(1, wcDen - 1);
      if (wcLeft === wcRight) wcRight = wcDen - 1;
      var wcTotal = wcDen * randInt(8, 20);
      var wcDiff = Math.abs(wcLeft - wcRight) * wcTotal / wcDen;
      if (kind === '20260302test') {
        var seqUsed = randInt(1, wcDen - 2);
        var seqRemainNum = wcDen - seqUsed;
        var seqSecondDen = [2, 4, 5][randInt(0, 2)];
        var seqSecondNum = randInt(1, seqSecondDen - 1);
        var seqAns = frac(seqRemainNum * (seqSecondDen - seqSecondNum), wcDen * seqSecondDen);
        return {
          q: '一桶果汁先用掉 ' + fracText(seqUsed, wcDen) + '，剩下的再用掉 ' + fracText(seqSecondNum, seqSecondDen) + '，最後還剩幾分之幾桶？',
          answer: fracText(seqAns.n, seqAns.d),
          hint: '先算第一次剩下幾分之幾，再把那一部分乘上第二次剩下的比例。'
        };
      }
      return {
        q: wcTotal + ' 顆糖果中，小明拿了 ' + fracText(wcLeft, wcDen) + '，小華拿了 ' + fracText(wcRight, wcDen) + '，兩人相差幾顆？',
        answer: String(wcDiff),
        hint: '先分別算出兩人的分量，再用較多減較少。'
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

    if (kind === 'u2_frac_addsub_life') {
      var flDen = [4, 5, 6, 8][randInt(0, 3)];
      var flA = randInt(1, flDen - 2);
      var flB = randInt(1, flDen - flA - 1);
      var flRes = frac(flA + flB, flDen);
      return {
        q: '小明早上喝了 ' + fracText(flA, flDen) + ' 瓶果汁，下午又喝了 ' + fracText(flB, flDen) + ' 瓶，一共喝了多少瓶？',
        answer: fracText(flRes.n, flRes.d),
        hint: '同分母分數先把分子相加，再看要不要約分。'
      };
    }

    if (kind === 'u6_frac_dec_convert') {
      var convChoices = [
        { n: 1, d: 2, ans: '0.5' },
        { n: 1, d: 4, ans: '0.25' },
        { n: 3, d: 4, ans: '0.75' },
        { n: 1, d: 5, ans: '0.2' },
        { n: 3, d: 5, ans: '0.6' }
      ];
      var conv = convChoices[randInt(0, convChoices.length - 1)];
      return {
        q: '把分數 ' + fracText(conv.n, conv.d) + ' 改寫成小數。',
        answer: conv.ans,
        hint: '先想分母能不能改成 10 或 100，再寫成對應的小數。'
      };
    }

    if (kind === 'are_to_m2') {
      var areVal = randInt(2, 30);
      return {
        q: areVal + ' 公畝 = 幾平方公尺？',
        answer: String(areVal * 100),
        hint: '1 公畝 = 100 平方公尺。大單位換小單位要乘。'
      };
    }

    if (kind === 'ha_to_m2') {
      var haVal = randInt(2, 25);
      return {
        q: haVal + ' 公頃 = 幾平方公尺？',
        answer: String(haVal * 10000),
        hint: '1 公頃 = 10000 平方公尺。'
      };
    }

    if (kind === 'km2_to_ha') {
      var km2Tenths = randInt(5, 30);
      return {
        q: (km2Tenths / 10).toFixed(1) + ' 平方公里 = 幾公頃？',
        answer: String(km2Tenths * 10),
        hint: '1 平方公里 = 100 公頃，所以乘 100。'
      };
    }

    if (kind === 'liter_to_ml') {
      var literTenths = randInt(2, 19);
      return {
        q: (literTenths / 10).toFixed(1) + ' L = 幾 mL？',
        answer: String(literTenths * 100),
        hint: '1 L = 1000 mL，小數公升換毫升直接乘 1000。'
      };
    }

    if (kind === 'mixed_units') {
      var muMeters = randInt(1, 3);
      var muWidth = randInt(20, 80);
      var muHeight = randInt(10, 40);
      return {
        q: '長方體長 ' + muMeters + ' 公尺、寬 ' + muWidth + ' 公分、高 ' + muHeight + ' 公分，體積是多少立方公分？',
        answer: String(muMeters * 100 * muWidth * muHeight),
        hint: '先把 ' + muMeters + ' 公尺換成 ' + (muMeters * 100) + ' 公分，再用長×寬×高。'
      };
    }

    if (kind === 'composite' || kind === 'composite3') {
      var compL = randInt(5, 12);
      var compH = randInt(3, 8);
      var compW1 = randInt(2, 6);
      var compW2 = randInt(2, 6);
      var compAns = compL * compH * (compW1 + compW2);
      if (kind === 'composite3') {
        var compW3 = randInt(2, 6);
        return {
          q: '把形體分成三個長方體：A 長 ' + compL + '、寬 ' + compW1 + '、高 ' + compH + '；B 長 ' + compL + '、寬 ' + compW2 + '、高 ' + compH + '；C 長 ' + compL + '、寬 ' + compW3 + '、高 ' + compH + '。總體積是多少立方公分？',
          answer: String(compL * compH * (compW1 + compW2 + compW3)),
          hint: '先各自算三塊的體積，再全部相加。'
        };
      }
      return {
        q: '把形體分成兩個長方體：A 長 ' + compL + '、寬 ' + compW1 + '、高 ' + compH + '；B 長 ' + compL + '、寬 ' + compW2 + '、高 ' + compH + '。總體積是多少立方公分？',
        answer: String(compAns),
        hint: '複合形體先切成兩塊，各算體積後再相加。'
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

    if (kind === 'u1_average' || kind === 'general' || kind.indexOf('average') >= 0 || kind === 'shopping_two_step' || kind === 'table_stats') {
      var avgCount = randInt(3, 5);
      var avgVal = randInt(15, 50);
      var avgTotal = avgVal * avgCount;
      return {
        q: avgTotal + ' 顆糖果平均分給 ' + avgCount + ' 個人，每人分到幾顆？',
        answer: String(avgVal),
        hint: '平均 = 總數 ÷ 人數 = ' + avgTotal + ' ÷ ' + avgCount + '。'
      };
    }

    if (kind === 'u3_money' || kind === 'make_change' || kind === 'buy_many' || mod.indexOf('money') >= 0) {
      var priceA = randInt(15, 80);
      var priceB = randInt(10, 60);
      var paid = priceA + priceB + randInt(5, 50);
      var change = paid - priceA - priceB;
      return {
        q: '小明買了 ' + priceA + ' 元和 ' + priceB + ' 元的東西，付了 ' + paid + ' 元，找零多少元？',
        answer: String(change),
        hint: '找零 = 付的錢 - 花掉的錢 = ' + paid + ' - ' + priceA + ' - ' + priceB + '。'
      };
    }

    if (kind === 'u4_discount_percent' || kind === 'discount' || kind.indexOf('percent') >= 0) {
      var discounts = [7, 8, 9];
      var discIdx = randInt(0, 2);
      var discVal = discounts[discIdx];
      var origPrice = randInt(2, 20) * 10;
      var salePrice = origPrice * discVal / 10;
      return {
        q: '商品原價 ' + origPrice + ' 元，打 ' + discVal + ' 折，售價多少元？',
        answer: String(salePrice),
        hint: '打 ' + discVal + ' 折 = 原價 × ' + discVal + '/10 = ' + origPrice + ' × ' + discVal + ' ÷ 10。'
      };
    }

    if (kind === 'cheng_increase') {
      var chengPrice = randInt(20, 90) * 10;
      var chengPart = randInt(1, 6);
      return {
        q: '原價 ' + chengPrice + ' 元，加 ' + chengPart + ' 成後，新價格是多少元？',
        answer: String(chengPrice * (10 + chengPart) / 10),
        hint: '加 ' + chengPart + ' 成 = 原來變成 ' + (10 + chengPart) + '/10 倍。'
      };
    }

    if (kind === 'u5_ratio_proportion' || kind.indexOf('ratio') >= 0) {
      var ratioA = randInt(2, 6);
      var ratioB = randInt(2, 6);
      var multiplier = randInt(2, 8);
      var valA = ratioA * multiplier;
      var valB = ratioB * multiplier;
      return {
        q: '甲和乙的比是 ' + ratioA + '：' + ratioB + '，甲有 ' + valA + ' 個，乙有幾個？',
        answer: String(valB),
        hint: '甲 = ' + ratioA + ' 份，1 份 = ' + valA + ' ÷ ' + ratioA + ' = ' + multiplier + '，乙 = ' + ratioB + ' × ' + multiplier + '。'
      };
    }

    if (kind === 'u6_unit_decimal' || kind.indexOf('decimal') >= 0 || mod.indexOf('decimal') >= 0) {
      var dWA = randInt(1, 9);
      var dDA = randInt(1, 9);
      var dWB = randInt(1, 9);
      var dDB = randInt(1, 9);
      var tenths = (dWA * 10 + dDA) + (dWB * 10 + dDB);
      var dAnsW = Math.floor(tenths / 10);
      var dAnsD = tenths % 10;
      var dAns = dAnsD === 0 ? String(dAnsW) : dAnsW + '.' + dAnsD;
      return {
        q: '計算：' + dWA + '.' + dDA + ' + ' + dWB + '.' + dDB + ' = ?',
        answer: dAns,
        hint: '先對齊小數點：' + dWA + '.' + dDA + ' + ' + dWB + '.' + dDB + '，再從小數位加起。'
      };
    }

    if (kind === 'x10_shift') {
      var shiftBase = randInt(11, 98);
      var shiftDec = randInt(1, 9);
      var shiftPlaces = [1, 2, 3][randInt(0, 2)];
      var shiftDiv = 1;
      for (var sp = 0; sp < shiftPlaces; sp++) shiftDiv *= 10;
      var shiftAns = ((shiftBase * 10 + shiftDec) / 10) / shiftDiv;
      return {
        q: '計算：' + shiftBase + '.' + shiftDec + ' × 0.' + '0'.repeat(Math.max(0, shiftPlaces - 1)) + '1 = ?',
        answer: String(shiftAns),
        hint: '乘 0.1、0.01、0.001 時，小數點往左移。'
      };
    }

    if (kind === 'd_mul_int') {
      var miA = randInt(11, 79) / 10;
      var miB = randInt(2, 9);
      return {
        q: '計算：' + miA.toFixed(1) + ' × ' + miB + ' = ?',
        answer: String(Number((miA * miB).toFixed(1))),
        hint: '先當整數算，再把小數點放回去。'
      };
    }

    if (kind === 'd_div_int') {
      var diB = randInt(2, 8);
      var diAns = randInt(11, 89) / 10;
      var diA = Number((diAns * diB).toFixed(1));
      return {
        q: '計算：' + diA.toFixed(1) + ' ÷ ' + diB + ' = ?',
        answer: String(diAns),
        hint: '把被除數平均分成 ' + diB + ' 份，注意小數點位置。'
      };
    }

    if (kind === 'd_mul_d') {
      var mdA = randInt(11, 39) / 10;
      var mdB = randInt(11, 29) / 10;
      return {
        q: '計算：' + mdA.toFixed(1) + ' × ' + mdB.toFixed(1) + ' = ?',
        answer: String(Number((mdA * mdB).toFixed(2))),
        hint: '先忽略小數點做整數乘法，再數兩個因數一共有幾位小數。'
      };
    }

    if (kind === 'int_mul_d') {
      var imA = randInt(2, 9);
      var imB = randInt(11, 59) / 10;
      return {
        q: '計算：' + imA + ' × ' + imB.toFixed(1) + ' = ?',
        answer: String(Number((imA * imB).toFixed(1))),
        hint: '整數乘小數，也是一樣先當整數算，再放回小數點。'
      };
    }

    if (kind === 'd_add_sub') {
      var asA = randInt(11, 89) / 10;
      var asB = randInt(11, 49) / 10;
      var useAdd = randInt(0, 1) === 0;
      var asAns = useAdd ? asA + asB : asA - asB;
      return {
        q: '計算：' + asA.toFixed(1) + (useAdd ? ' + ' : ' - ') + asB.toFixed(1) + ' = ?',
        answer: String(Number(asAns.toFixed(1))),
        hint: '小數加減要先對齊小數點。'
      };
    }

    if (kind === 'u7_speed' || kind === 'displacement' || kind.indexOf('speed') >= 0) {
      var speedTime = randInt(2, 6);
      var speedRate = randInt(30, 80);
      var dist = speedRate * speedTime;
      return {
        q: '小明走了 ' + dist + ' 公尺，花了 ' + speedTime + ' 分鐘，每分鐘走幾公尺？',
        answer: String(speedRate),
        hint: '速率 = 距離 ÷ 時間 = ' + dist + ' ÷ ' + speedTime + '。'
      };
    }

    if (kind === 'u8_area_perimeter' || kind.indexOf('area') >= 0 || kind.indexOf('perimeter') >= 0) {
      var areaL = randInt(3, 15);
      var areaW = randInt(2, 10);
      return {
        q: '長方形長 ' + areaL + ' 公分、寬 ' + areaW + ' 公分，面積是多少平方公分？',
        answer: String(areaL * areaW),
        hint: '長方形面積 = 長 × 寬 = ' + areaL + ' × ' + areaW + '。'
      };
    }

    if (kind === 'u9_time_trip' || kind.indexOf('time') >= 0 || kind.indexOf('trip') >= 0) {
      var tHours = randInt(1, 5);
      var tMins = randInt(10, 50);
      var totalMins = tHours * 60 + tMins;
      return {
        q: '小華花了 ' + tHours + ' 小時 ' + tMins + ' 分鐘做作業，共花了幾分鐘？',
        answer: String(totalMins),
        hint: tHours + ' 小時 = ' + (tHours * 60) + ' 分鐘，再加 ' + tMins + ' 分鐘。'
      };
    }

    if (kind === 'temperature_change') {
      var tempStart = randInt(-3, 18);
      var tempDelta = randInt(2, 9);
      var goesUp = randInt(0, 1) === 0;
      return {
        q: '早上氣溫是 ' + tempStart + ' 度，之後' + (goesUp ? '上升' : '下降') + ' ' + tempDelta + ' 度，現在幾度？',
        answer: String(goesUp ? tempStart + tempDelta : tempStart - tempDelta),
        hint: '上升用加法，下降用減法。先看變化方向。'
      };
    }

    if (kind === 'clock_angle') {
      var hour = randInt(1, 11);
      var minute = [0, 30][randInt(0, 1)];
      var minuteAngle = minute * 6;
      var hourAngle = hour * 30 + minute * 0.5;
      var angle = Math.abs(hourAngle - minuteAngle);
      angle = angle > 180 ? 360 - angle : angle;
      return {
        q: '在 ' + hour + ':' + (minute === 0 ? '00' : String(minute)) + '，時針和分針的較小夾角是多少度？',
        answer: String(angle),
        hint: '分針每分鐘走 6 度，時針每小時走 30 度，還會隨分鐘再移動。'
      };
    }

    if (kind === 'sector_central_angle') {
      var secDen = [2, 3, 4, 5, 6, 8, 9, 10, 12][randInt(0, 8)];
      var secNum = randInt(1, secDen - 1);
      return {
        q: '一個扇形占整個圓的 ' + fracText(secNum, secDen) + '，圓心角是多少度？',
        answer: String(360 * secNum / secDen),
        hint: '整個圓是 360 度，先求 ' + fracText(secNum, secDen) + ' 的 360 度。'
      };
    }

    if (kind === 'gcd_word') {
      var gcdBase = randInt(2, 9);
      var gcdA = gcdBase * randInt(4, 9);
      var gcdB = gcdBase * randInt(3, 8);
      return {
        q: '有兩條繩子長 ' + gcdA + ' 公分和 ' + gcdB + ' 公分，要剪成一樣長且不能有剩，最長每段幾公分？',
        answer: String(gcd(gcdA, gcdB)),
        hint: '題目要「剪成一樣長且不能剩」，找最大公因數。'
      };
    }

    if (kind === 'lcm_word') {
      var lcmA = randInt(3, 6);
      var lcmB = randInt(4, 8);
      return {
        q: '甲車每 ' + lcmA + ' 分鐘到一次，乙車每 ' + lcmB + ' 分鐘到一次。兩車同時到站後，最少再過幾分鐘會再同時到？',
        answer: String(lcmA * lcmB / gcd(lcmA, lcmB)),
        hint: '要找兩個週期再次同時出現，找最小公倍數。'
      };
    }

    if (kind === 'prime_or_composite') {
      var primeChoices = [11, 13, 17, 19, 23, 29];
      var compositeChoices = [12, 18, 21, 24, 27, 28];
      var usePrime = randInt(0, 1) === 0;
      var pcValue = usePrime ? primeChoices[randInt(0, primeChoices.length - 1)] : compositeChoices[randInt(0, compositeChoices.length - 1)];
      return {
        q: pcValue + ' 是質數還是合數？',
        answer: usePrime ? '質數' : '合數',
        hint: '試著找除了 1 和自己之外，還能不能整除它的數。'
      };
    }

    if (kind === 'line_max_month') {
      var lmBase = randInt(20, 40);
      var lmPeak = randInt(0, 3);
      var lmValues = [lmBase, lmBase + 3, lmBase + 6, lmBase + 9];
      lmValues[0] += randInt(0, 2);
      lmValues[1] += randInt(0, 2);
      lmValues[2] += randInt(0, 2);
      lmValues[3] += randInt(0, 2);
      var lmTmp = lmValues[lmPeak];
      lmValues[lmPeak] = Math.max.apply(null, lmValues) + randInt(1, 3);
      lmValues[(lmPeak + 1) % 4] = lmTmp;
      return {
        q: '1月：' + lmValues[0] + '\n2月：' + lmValues[1] + '\n3月：' + lmValues[2] + '\n4月：' + lmValues[3] + '\n哪一個月份的數值最高？',
        answer: String(lmPeak + 1) + '月',
        hint: '把四個月份的數字逐一比較，找最大的那個。'
      };
    }

    if (kind === 'line_omit_rule') {
      var loStart = randInt(8, 20);
      var loStep = randInt(2, 6);
      return {
        q: '數列依序增加同樣的數：' + loStart + '、' + (loStart + loStep) + '、□、' + (loStart + loStep * 3) + '。□ 是多少？',
        answer: String(loStart + loStep * 2),
        hint: '先看前後兩項差幾，再把規律補回去。'
      };
    }

    if (kind === 'line_trend') {
      var ltFirst = randInt(20, 35);
      var ltDelta = [-3, 0, 4][randInt(0, 2)];
      return {
        q: '3月：' + ltFirst + '\n4月：' + (ltFirst + ltDelta) + '\n從 3月 到 4月 的趨勢是？（填：上升/下降/不變）',
        answer: ltDelta > 0 ? '上升' : (ltDelta < 0 ? '下降' : '不變'),
        hint: '比較後一個月和前一個月，是變大、變小，還是一樣。'
      };
    }

    if (kind === 'perp_bisector_property') {
      return {
        q: '線段 AB 的垂直平分線上有一點 P，P 到 A 和 B 的距離關係是什麼？（填：PA=PB）',
        answer: 'PA=PB',
        hint: '垂直平分線上的點，到線段兩端的距離相等。'
      };
    }

    if (kind === 'perp_bisector_converse') {
      return {
        q: '如果點 P 到 A、B 兩點的距離相等，那麼 P 一定在 AB 的垂直平分線上嗎？（填：是/否）',
        answer: '是',
        hint: '距離兩端相等的點，會落在線段的垂直平分線上。'
      };
    }

    if (kind === 'symmetry_axes') {
      var shapes = [
        { name: '正方形', answer: '4' },
        { name: '長方形（非正方形）', answer: '2' },
        { name: '等邊三角形', answer: '3' }
      ];
      var shape = shapes[randInt(0, shapes.length - 1)];
      return {
        q: shape.name + ' 有幾條對稱軸？',
        answer: shape.answer,
        hint: '想像把圖形對折，能完全重合的折線就是對稱軸。'
      };
    }

    if (kind === 'place_value_digit') {
      var pvNumber = String(randInt(2, 9)) + String(randInt(0, 9)) + String(randInt(0, 9)) + ',' + String(randInt(0, 9)) + String(randInt(0, 9)) + String(randInt(0, 9)) + ',' + String(randInt(0, 9)) + String(randInt(0, 9)) + String(randInt(0, 9));
      var pvDigits = pvNumber.replace(/,/g, '');
      return {
        q: '在 ' + pvNumber + ' 裡，百萬位上的數字是多少？',
        answer: pvDigits.charAt(pvDigits.length - 7),
        hint: '從右邊開始數：個、十、百、千、萬、十萬、百萬。'
      };
    }

    if (kind === 'place_value_truncate') {
      var ptNumber = randInt(100, 999) * 1000000 + randInt(1000, 9999) * 100;
      var ptAnswer = Math.floor(ptNumber / 10000000) * 10000000;
      return {
        q: '把 ' + ptNumber + ' 無條件捨去到千萬位，得到多少？',
        answer: String(ptAnswer),
        hint: '無條件捨去就是後面的位數全部直接變 0。'
      };
    }

    if (kind === 'place_value_yi_wan') {
      var yi = randInt(1, 5);
      var wan = randInt(1000, 9999);
      var rest = randInt(100, 9999);
      return {
        q: yi + ' 億 ' + wan + ' 萬 ' + rest + ' 表示多少？',
        answer: String(yi * 100000000 + wan * 10000 + rest),
        hint: '1 億 = 100000000，1 萬 = 10000，先分段換成數字再相加。'
      };
    }

    if (kind === 'large_numbers_comparison') {
      var lnA = randInt(20000, 50000);
      var lnB = randInt(20000, 50000);
      var lnKg = lnA * 1000;
      var lnTon = lnB;
      var lnAnswer = lnA > lnB ? lnA : lnB;
      return {
        q: '比較 ' + lnKg + ' 公斤 和 ' + lnTon + ' 公噸，較大的是多少公噸？',
        answer: String(lnAnswer),
        hint: '先把公斤換成公噸：1000 公斤 = 1 公噸。換成同單位後再比較。'
      };
    }

    if (kind === 'solve_ax') {
      var ax = randInt(2, 9);
      var axAns = randInt(3, 12);
      return {
        q: '解方程：' + ax + 'x = ' + (ax * axAns) + '，x = ？',
        answer: String(axAns),
        hint: '要讓 x 單獨留下，就把兩邊都除以 ' + ax + '。'
      };
    }

    if (kind === 'solve_x_div_d') {
      var xd = randInt(2, 8);
      var xdAns = randInt(4, 15);
      return {
        q: '解方程：x ÷ ' + xd + ' = ' + xdAns + '，x = ？',
        answer: String(xd * xdAns),
        hint: 'x ÷ ' + xd + ' = ' + xdAns + '，兩邊同乘 ' + xd + '。'
      };
    }

    if (kind === 'solve_x_plus_a') {
      var xa = randInt(3, 15);
      var xaAns = randInt(4, 20);
      return {
        q: '解方程：x + ' + xa + ' = ' + (xa + xaAns) + '，x = ？',
        answer: String(xaAns),
        hint: '要找 x，就把等號另一邊減掉 ' + xa + '。'
      };
    }

    if (kind === 'division_application') {
      var daCost = randInt(200, 900) * 10;
      var daNeed = randInt(8, 20);
      var daEnough = randInt(0, 1) === 0;
      var daFunds = daEnough ? daCost * daNeed + randInt(100, 900) : daCost * daNeed - randInt(100, daCost - 10);
      return {
        q: '每套桌椅 ' + daCost + ' 元，現有 ' + daFunds + ' 元，想買 ' + daNeed + ' 套，夠不夠？（填：夠/不夠）',
        answer: daEnough ? '夠' : '不夠',
        hint: '先算需要總共多少元，再和現有金額比較。'
      };
    }

    if (kind === 'unit_price') {
      var upCount = randInt(3, 9);
      var upUnit = randInt(8, 25);
      var upTotal = upCount * upUnit;
      return {
        q: upCount + ' 個相同的麵包共 ' + upTotal + ' 元，每個多少元？',
        answer: String(upUnit),
        hint: '每個多少元 = 總價 ÷ 數量 = ' + upTotal + ' ÷ ' + upCount + '。'
      };
    }

    if (kind === 'proportional_split') {
      var psA = randInt(2, 5);
      var psB = randInt(2, 5);
      var psUnit = randInt(3, 8);
      var psTotal = (psA + psB) * psUnit;
      return {
        q: '把 ' + psTotal + ' 顆糖果按 ' + psA + '：' + psB + ' 分給甲和乙，甲分到幾顆？',
        answer: String(psA * psUnit),
        hint: '先算總份數，再用總量 ÷ 總份數求 1 份。'
      };
    }

    if (kind === 'unit_convert') {
      var ucMeters = randInt(2, 9);
      return {
        q: ucMeters + ' 公尺 = 幾公分？',
        answer: String(ucMeters * 100),
        hint: '1 公尺 = 100 公分，大單位換小單位要乘。'
      };
    }

    if (kind === 'u10_multi_step' || kind === 'multi_step') {
      var boxCount = randInt(3, 8);
      var perBox = randInt(5, 15);
      var eaten = randInt(1, boxCount * perBox - 1);
      return {
        q: '每盒有 ' + perBox + ' 個餅乾，買了 ' + boxCount + ' 盒，吃掉 ' + eaten + ' 個，還剩幾個？',
        answer: String(boxCount * perBox - eaten),
        hint: '先算總數 = ' + perBox + ' × ' + boxCount + ' = ' + (boxCount * perBox) + '，再減掉 ' + eaten + '。'
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
