/*  wrong_detail_data.js  –  kind → {cause, concept, tutor} rule table
 *  Browser IIFE – exposes window.AIMathWrongDetailData
 *
 *  Rules are matched top-to-bottom, first match wins.
 *  Each rule can match on:
 *    kinds       – exact kind values (array)
 *    kindContains – substring match on kind (string)
 *    mods        – exact mod values (array)
 *    modContains – substring match on mod (string)
 *    errContains – substring match on errType (array of strings, any match)
 *
 *  To add a new kind: insert a rule at the appropriate priority position.
 */
(function(){
  'use strict';

  var RULES = [
    {
      kinds: ['generic_fraction_word', 'fraction_of_quantity'],
      detail: {
        cause: '分量應用題容易把對象搞混，不確定是全量的幾分之幾還是剩下的幾分之幾。',
        concept: '先找出全量，再決定是用全量乘分數，還是先求剩餘再計算。',
        tutor: '先畫線段圖標出全量與已用量，再做 3 題同結構換數字題。'
      }
    },
    {
      kinds: ['reverse_fraction'],
      detail: {
        cause: '反向分數題容易把乘除方向顛倒。',
        concept: '先找出剩下佔全部的幾分之幾，再用剩餘量反推原量。',
        tutor: '先畫出花掉與剩下的比例，再用 3 題反向題練習。'
      }
    },
    {
      kinds: ['cube_cm3', 'cube_find_edge', 'surface_area_cube'],
      detail: {
        cause: '容易把邊長、體積、表面積公式混在一起。',
        concept: '先確認題目問的是體積還是表面積，再代對公式。',
        tutor: '先口頭說公式用途，再練 3 題只改數字的正方體題。'
      }
    },
    {
      kinds: ['rect_cm3', 'rect_find_height', 'volume_rect_prism', 'base_area_h'],
      detail: {
        cause: '長方體題常把邊長對錯或忽略單位。',
        concept: '體積 = 長 × 寬 × 高，或底面積 × 高，答案要保留立方單位。',
        tutor: '先畫立體圖標三邊，再做 5 題只換一個數字的對照題。'
      }
    },
    {
      modContains: 'fraction-word',
      detail: {
        cause: '文字題常在題意轉算式時卡住。',
        concept: '先圈關鍵詞，再拆成已知、未知、算式三步。',
        tutor: '先口述算式理由，再下筆做同類題。'
      }
    },
    {
      kinds: ['original', 'remain', 'part_to_total', 'compare', 'remain_multi'],
      detail: {
        cause: '分數衝刺題常把「原量、部分量、剩餘量」之間的關係混在一起。',
        concept: '先確認題目要找原量、部分還是剩下，再決定用乘法、減法或反推除法。',
        tutor: '先畫線段圖標出整體與部分，再做 3 題同結構換數字題。'
      }
    },
    {
      kinds: ['add_like', 'sub_like'],
      detail: {
        cause: '同分母分數計算容易忘記「分母不變，只算分子」。',
        concept: '同分母加減時，先看分子做加減，分母保持不變，最後再約分。',
        tutor: '先用 3 題同分母分數口算，再把結果化成最簡分數。'
      }
    },
    {
      kinds: ['add_unlike', 'sub_unlike'],
      detail: {
        cause: '異分母分數常在通分時把新分子或新分母寫錯。',
        concept: '先找公分母，兩個分數都改寫成同分母，再做加減。',
        tutor: '先把每題的公分母寫出來，再做 3 題異分母加減練習。'
      }
    },
    {
      kinds: ['equivalent', 'simplify'],
      detail: {
        cause: '等值分數和約分題容易漏掉公因數，或把分子分母只約一邊。',
        concept: '分子和分母要同乘或同除相同的數，才會保持等值。',
        tutor: '先找公因數或缺的倍數，再做 4 題等值分數與約分題。'
      }
    },
    {
      kinds: ['mixed_convert', 'reciprocal', 'mul', 'mul_int'],
      detail: {
        cause: '分數乘法和互換題容易在假分數、帶分數或倒數規則之間混掉。',
        concept: '先判斷是互換、求倒數，還是乘法；帶分數先改假分數，再算或再化回去。',
        tutor: '先做分數互換和倒數暖身，再做 3 題分數乘法。'
      }
    },
    {
      kinds: ['word_compare', '20260302test', 'national_bank_source'],
      detail: {
        cause: '來源題或分數文字比較題容易卡在「先算各自幾分之幾，再比較剩多少或差多少」。',
        concept: '先把每個人的分量分別算出來，再比較誰多誰少或剩多少。',
        tutor: '先畫線段圖分別表示兩個量，再做 2 題分數比較或剩餘題。'
      }
    },
    {
      kindContains: 'fraction',
      modContains: 'fraction',
      matchOr: true,
      detail: {
        cause: '分數題常在通分、約分或運算規則混用時出錯。',
        concept: '先判斷加減還是乘除，再做通分或約分。',
        tutor: '用通分格線法練 10 分鐘，再回到同類題。'
      }
    },
    {
      kinds: ['u2_frac_addsub_life'],
      detail: {
        cause: '生活分數題常把同分母相加減、剩餘量與比較量搞混。',
        concept: '先判斷是合起來、拿走後剩下，還是比較誰多誰少，再決定加減。',
        tutor: '先把每段量畫成同一個整體，再做 3 題分數生活題。'
      }
    },
    {
      kinds: ['u6_frac_dec_convert'],
      detail: {
        cause: '分數和小數轉換時，容易忘記 1/10、1/100 對應到小數點位置。',
        concept: '先看分母是不是 10、100、1000，再把分數改寫成對應的小數。',
        tutor: '先做分數↔小數對照表，再做 5 題轉換題。'
      }
    },
    {
      kinds: ['are_to_m2', 'ha_to_m2', 'km2_to_ha', 'liter_to_ml', 'mixed_units'],
      detail: {
        cause: '單位換算題常在「大換小乘、小換大除」或平方單位倍數上搞混。',
        concept: '先寫出 1 個大單位等於多少小單位，再判斷要乘還是除。面積單位要特別注意是平方關係。',
        tutor: '先把單位階梯寫出來，再做 5 題同單位系統換算。'
      }
    },
    {
      kinds: ['composite', 'composite3'],
      detail: {
        cause: '複合形體體積題容易少切一塊，或切開後某段長寬高對錯。',
        concept: '先把複合形體拆成 2 或 3 個長方體，分別算體積後再相加。',
        tutor: '先畫分塊圖並標出每塊尺寸，再做 2 題複合體積題。'
      }
    },
    {
      kindContains: 'volume',
      modContains: 'volume',
      kindContains2: 'cm3',
      matchOr: true,
      detail: {
        cause: '空間量題常把公式或單位混掉。',
        concept: '先確認題目要的是體積、面積或邊長，再代公式。',
        tutor: '先畫圖標示量，再做 3 題對照練習。'
      }
    },
    {
      kinds: ['u1_average', 'general', 'shopping_two_step', 'table_stats'],
      kindContains: 'average',
      matchOr: true,
      detail: {
        cause: '平均數題目容易把「總和」和「個數」搞混，或漏加某一項。',
        concept: '平均 = 總和 ÷ 個數。先確認有幾個數，再加總，最後除。',
        tutor: '先列出所有數字核對，再做 3 題類似平均題。'
      }
    },
    {
      kinds: ['u3_money', 'make_change', 'buy_many'],
      modContains: 'money',
      matchOr: true,
      detail: {
        cause: '金錢應用題常在找零或單價×數量時算錯。',
        concept: '先列出每項花費，加總後再用總金額去減。',
        tutor: '先用表格整理花費，再做 3 題換數字的找零題。'
      }
    },
    {
      kinds: ['u4_discount_percent', 'discount'],
      kindContains: 'percent',
      matchOr: true,
      detail: {
        cause: '百分比或折扣題容易把「打幾折」和「減多少%」搞混。',
        concept: '打 8 折 = 原價 × 0.8 = 原價 × 80%。先把折數換成百分比再計算。',
        tutor: '先口述折扣意義，再做 3 題不同折扣的對照練習。'
      }
    },
    {
      kinds: ['cheng_increase'],
      detail: {
        cause: '成數增加題常把「加幾成」誤當成只乘成數本身。',
        concept: '加 4 成 = 原來的 1.4 倍。先把成數換成百分率，再把原價和增加後一起想。',
        tutor: '先把 1 成到 9 成各自換成百分率，再做 3 題成數增加題。'
      }
    },
    {
      kinds: ['u5_ratio_proportion'],
      kindContains: 'ratio',
      matchOr: true,
      detail: {
        cause: '比例題容易把前項、後項搞反，或約比時漏掉步驟。',
        concept: '比 = 前項：後項。化簡比要兩邊同除以最大公因數。',
        tutor: '先圈出前項和後項，再做 3 題類似比例題。'
      }
    },
    {
      kinds: ['u6_unit_decimal'],
      kindContains: 'decimal',
      modContains: 'decimal',
      matchOr: true,
      detail: {
        cause: '小數題常在小數點對位或單位換算時出錯。',
        concept: '小數加減要對齊小數點；乘法先忽略小數點算，再數總共幾位小數。',
        tutor: '先在草稿紙對齊小數點，再做 3 題只改數字的練習。'
      }
    },
    {
      kinds: ['x10_shift', 'd_mul_int', 'd_div_int', 'd_mul_d', 'int_mul_d', 'd_add_sub'],
      detail: {
        cause: '小數運算題容易把小數點移動規則和直式對位規則混在一起。',
        concept: '先判斷是加減、乘法、除法，還是乘 10/100/1000，再用對應的小數點規則。',
        tutor: '先估算答案大小，再做 4 題同一種小數規則題。'
      }
    },
    {
      kinds: ['u7_speed', 'displacement'],
      kindContains: 'speed',
      matchOr: true,
      detail: {
        cause: '速率題常把距離、時間、速率三量的關係搞混。',
        concept: '速率 = 距離 ÷ 時間。先確定已知哪兩個量，再求第三個。',
        tutor: '先畫速率三角形，再做 3 題求不同量的對照練習。'
      }
    },
    {
      kinds: ['u8_area_perimeter'],
      kindContains: 'area',
      kindContains2: 'perimeter',
      matchOr: true,
      detail: {
        cause: '面積和周長公式容易搞混，或忘了不同形狀有不同公式。',
        concept: '長方形面積 = 長 × 寬，周長 = (長 + 寬) × 2。先確認求面積還是周長。',
        tutor: '先在圖上標出各邊長，再做 3 題同類型練習。'
      }
    },
    {
      kinds: ['u9_time_trip'],
      kindContains: 'time',
      kindContains2: 'trip',
      matchOr: true,
      detail: {
        cause: '時間題常在進位（60分=1時）或跨午、跨日時算錯。',
        concept: '先統一單位（全換分鐘或全換小時），再做加減。',
        tutor: '先在時間軸上標出起點和終點，再做 3 題類似時間題。'
      }
    },
    {
      kinds: ['temperature_change'],
      detail: {
        cause: '溫度題容易把升高和降低的方向看反。',
        concept: '先看是上升還是下降，再用加法或減法更新溫度。',
        tutor: '先在數線上標出起點和變化量，再做 3 題溫度變化題。'
      }
    },
    {
      kinds: ['unit_price'],
      detail: {
        cause: '單價題常把總價、數量、每單位價格三個量的除法方向寫反。',
        concept: '單價 = 總價 ÷ 數量。先確認題目是求每 1 個、每 1 公斤，還是每 1 公尺。',
        tutor: '先把總價和數量列成表格，再做 3 題單價題。'
      }
    },
    {
      kinds: ['clock_angle', 'sector_central_angle'],
      detail: {
        cause: '角度題常在把一整圈 360 度分成部分時算錯。',
        concept: '先找整圈 360 度，再看題目占了幾分之幾或時鐘兩針各走到哪裡。',
        tutor: '先畫圓並標 12 等分，再做 3 題圓心角或時鐘夾角題。'
      }
    },
    {
      kinds: ['gcd_word', 'lcm_word', 'prime_or_composite'],
      detail: {
        cause: '因數倍數題容易搞混「分得剛好」要用最大公因數，還是「同時再出現」要用最小公倍數。',
        concept: '分裝剛好看公因數；週期同時發生看公倍數；質數只有 1 和自己兩個因數。',
        tutor: '先判斷題目是分小還是排時間，再做 4 題因數倍數題。'
      }
    },
    {
      kinds: ['line_max_month', 'line_omit_rule', 'line_trend'],
      detail: {
        cause: '折線圖題常在讀表、找最大值或判斷趨勢時看錯相鄰資料。',
        concept: '先逐點讀出資料，再比較大小或看前後是上升、下降還是不變。',
        tutor: '先把圖上的數據抄成表格，再做 3 題折線圖判讀。'
      }
    },
    {
      kinds: ['perp_bisector_property', 'perp_bisector_converse', 'symmetry_axes'],
      detail: {
        cause: '線對稱題常在性質與逆命題之間混淆，或忘記常見圖形的對稱軸數。',
        concept: '垂直平分線上的點到線段兩端距離相等；距離相等的點也在垂直平分線上。對稱軸要看圖形左右或上下是否能重合。',
        tutor: '先摺紙或畫對稱線，再做 3 題線對稱與垂直平分線題。'
      }
    },
    {
      kinds: ['place_value_digit', 'place_value_truncate', 'place_value_yi_wan', 'large_numbers_comparison'],
      detail: {
        cause: '大數題常在位值位置、億萬換寫或單位轉換後比較大小時出錯。',
        concept: '先從右往左定位，再決定取哪一位、要不要捨去，或先換成同單位再比較。',
        tutor: '先畫位值表，再做 4 題大數位值與比較題。'
      }
    },
    {
      kinds: ['solve_ax', 'solve_x_div_d', 'solve_x_plus_a'],
      detail: {
        cause: '等量公理題常把移項方向或乘除關係做反。',
        concept: '未知數在哪一邊，就對等式兩邊做相同的逆運算，把 x 單獨留下。',
        tutor: '先說出這題要用加減還是乘除的逆運算，再做 3 題一元一次暖身題。'
      }
    },
    {
      kinds: ['division_application'],
      detail: {
        cause: '除法應用題常在判斷「夠不夠」時，只算出商卻忘了回到情境比較。',
        concept: '先用總量 ÷ 每份成本或數量求能換幾份，再跟題目要求比較。',
        tutor: '先列出總量、每份、需求三欄，再做 3 題夠不夠的除法應用題。'
      }
    },
    {
      kinds: ['proportional_split'],
      detail: {
        cause: '按比例分配題容易把總份數和每一部分的倍數關係搞混。',
        concept: '先把比值加起來求總份數，再用總量 ÷ 總份數算出 1 份。',
        tutor: '先畫比例條圖，再做 3 題按比分配題。'
      }
    },
    {
      kinds: ['unit_convert'],
      detail: {
        cause: '單位換算題常忘記大單位和小單位之間差幾倍。',
        concept: '先確認是大換小還是小換大，再用 10、100、1000 的倍數去乘除。',
        tutor: '先寫出單位階梯，再做 5 題同單位系統換算題。'
      }
    },
    {
      kinds: ['u10_multi_step', 'multi_step'],
      detail: {
        cause: '多步驟題容易在中間步驟算錯或漏掉一步。',
        concept: '先把大問題拆成小步驟，每步只做一件事，做完再串起來。',
        tutor: '先把每一步的算式寫出來，核對後再合併，最後做 2 題類似題。'
      }
    },
    {
      errContains: ['careless', '粗心'],
      detail: {
        cause: '概念大致正確，但計算或抄寫時出現小錯。',
        concept: '做完後先估算量級，再做一次反向檢查。',
        tutor: '每題固定留 15 秒做符號、位值、單位檢查。'
      }
    }
  ];

  var DEFAULT_DETAIL = {
    cause: '可能卡在題意理解或步驟拆解。',
    concept: '先拆成已知、未知、關係，每一步只做一個動作。',
    tutor: '先示範一題完整思路，再讓學生獨立完成兩題。'
  };

  /**
   * Look up the first matching rule for the given kind/mod/errType.
   * @param {string} kind
   * @param {string} mod
   * @param {string} errType
   * @returns {{ cause: string, concept: string, tutor: string }}
   */
  function lookup(kind, mod, errType) {
    for (var i = 0; i < RULES.length; i++) {
      if (_matches(RULES[i], kind, mod, errType)) return RULES[i].detail;
    }
    return DEFAULT_DETAIL;
  }

  function _matches(rule, kind, mod, errType) {
    var hits = [];

    if (rule.kinds) {
      hits.push(rule.kinds.indexOf(kind) >= 0);
    }
    if (rule.kindContains) {
      hits.push(kind.indexOf(rule.kindContains) >= 0);
    }
    if (rule.kindContains2) {
      hits.push(kind.indexOf(rule.kindContains2) >= 0);
    }
    if (rule.mods) {
      hits.push(rule.mods.indexOf(mod) >= 0);
    }
    if (rule.modContains) {
      hits.push(mod.indexOf(rule.modContains) >= 0);
    }
    if (rule.errContains) {
      var anyErr = false;
      for (var j = 0; j < rule.errContains.length; j++) {
        if (errType.indexOf(rule.errContains[j]) >= 0) { anyErr = true; break; }
      }
      hits.push(anyErr);
    }

    if (!hits.length) return false;
    if (rule.matchOr) {
      for (var k = 0; k < hits.length; k++) { if (hits[k]) return true; }
      return false;
    }
    for (var m = 0; m < hits.length; m++) { if (!hits[m]) return false; }
    return true;
  }

  window.AIMathWrongDetailData = {
    RULES: RULES,
    DEFAULT_DETAIL: DEFAULT_DETAIL,
    lookup: lookup
  };
})();
