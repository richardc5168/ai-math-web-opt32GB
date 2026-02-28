/**
 * hint_engine.js — 全站提示優化引擎 v2.17
 *
 * 四級視覺鷹架系統：
 *  L1 觀念鎖定 — 圈重點、辨題型、基準切換警示
 *  L2 畫圖     — 動態 SVG 長條圖/數線/百格/3D 盒/位值圖/圓餅圖/對比圖
 *  L3 讀圖得分數 — 格子圖 + 色塊對應分數 + 位值分解 + 驗證加總
 *  L4 算式收斂 + 合理性檢查 — 分步公式 + ✅/❌ 檢核 + 填空框
 *
 * 額外功能：
 *  • L4 嚴格防洩漏（只到中間量，不給最終答案）
 *  • 錯因對應提示（MISCONCEPTION_MAP → 補救句）
 *  • 錯因診斷 UI（卡片式呈現 → 嚴重度色碼 → 重試按鈕）
 *  • 提示成效閉環（記錄看到哪層後答對）
 *  • 「基準量切換」視覺強化
 *
 * 回朔方式：URL ?hint_engine=off 或 localStorage aimath.hintEngine.enabled=0
 */
(function(){
  'use strict';

  /* ============================================================
   * 0. Feature toggle (rollback-safe)
   * ============================================================ */
  var ENABLE_KEY = 'aimath.hintEngine.enabled';
  var TRACK_KEY  = 'aimath.hintEffectiveness';

  function isEnabled(){
    var qs = new URLSearchParams(window.location.search || '');
    var q  = (qs.get('hint_engine') || '').toLowerCase();
    if (q === 'off' || q === '0' || q === 'false') return false;
    var v = localStorage.getItem(ENABLE_KEY);
    if (v === null) return true;
    return v !== '0' && v !== 'false' && v !== 'off';
  }

  /* ============================================================
   * 0b. Utility: extract fraction numbers from question text
   * ============================================================ */
  function extractFractions(text){
    var results = [];
    var t = String(text || '');
    /* Match mixed numbers first: N又a/b, N又b分之a */
    var reMixed1 = /(\d+)\s*又\s*(\d+)\s*[\/／]\s*(\d+)/g;
    var m;
    while ((m = reMixed1.exec(t)) !== null){
      var whole = parseInt(m[1],10);
      var num = parseInt(m[2],10);
      var den = parseInt(m[3],10);
      results.push({ num: whole * den + num, den: den, mixed: whole });
    }
    var reMixed2 = /(\d+)\s*又\s*(\d+)\s*分之\s*(\d+)/g;
    while ((m = reMixed2.exec(t)) !== null){
      var whole2 = parseInt(m[1],10);
      var den2 = parseInt(m[2],10);
      var num2 = parseInt(m[3],10);
      results.push({ num: whole2 * den2 + num2, den: den2, mixed: whole2 });
    }
    /* Match simple fractions: a/b, a／b (skip if already captured as part of mixed) */
    var re1 = /(?<!\d\s*又\s*)(\d+)\s*[\/／]\s*(\d+)/g;
    while ((m = re1.exec(t)) !== null){
      /* Check this isn't part of a mixed number already captured */
      var isDup = results.some(function(r){ return r.den === parseInt(m[2],10) && (r.num % r.den === parseInt(m[1],10) % parseInt(m[2],10) || r.num - (r.mixed||0)*r.den === parseInt(m[1],10)); });
      if (!isDup) results.push({ num: parseInt(m[1],10), den: parseInt(m[2],10) });
    }
    /* Match Chinese style: b分之a (skip if part of mixed) */
    var re2 = /(?<!\d\s*又\s*)(\d+)\s*分之\s*(\d+)/g;
    while ((m = re2.exec(t)) !== null){
      var isDup2 = results.some(function(r){ return r.den === parseInt(m[1],10) && (r.num - (r.mixed||0)*r.den === parseInt(m[2],10)); });
      if (!isDup2) results.push({ num: parseInt(m[2],10), den: parseInt(m[1],10) });
    }
    return results;
  }
  function extractIntegers(text){
    var results = [];
    var t = String(text || '').replace(/\d+\s*又\s*\d+\s*[\/／分]\s*[之]?\s*\d+/g, ''); /* strip mixed numbers */
    t = t.replace(/\d+\s*[\/／分]\s*[之]?\s*\d+/g, ''); /* strip fractions */
    var re = /(\d+)/g;
    var m;
    while ((m = re.exec(t)) !== null){ results.push(parseInt(m[1],10)); }
    return results;
  }
  function gcd(a, b){ a = Math.abs(a); b = Math.abs(b); while(b){ var t=b; b=a%b; a=t; } return a; }
  function lcm(a, b){ return a && b ? Math.abs(a*b)/gcd(a,b) : 0; }

  /* ============================================================
   * 1. 四級標籤定義
   * ============================================================ */
  var TIER_DEFS = [
    { level: 1, icon: '🔍', label: 'L1 觀念鎖定',          color: '#58a6ff', bg: 'rgba(88,166,255,.15)' },
    { level: 2, icon: '🖼️', label: 'L2 畫圖',              color: '#3fb950', bg: 'rgba(63,185,80,.15)' },
    { level: 3, icon: '📊', label: 'L3 讀圖得分數',         color: '#d29922', bg: 'rgba(210,153,34,.15)' },
    { level: 4, icon: '📝', label: 'L4 算式收斂＋合理性檢查', color: '#f85149', bg: 'rgba(248,81,73,.15)' }
  ];

  /* ============================================================
   * 2. 四步模板系統 — L1圈 → L2圖 → L3讀 → L4式查
   * ============================================================ */
  var TEMPLATE_MAP = {
    /* ------- 分數加減 ------- */
    fracAdd: {
      L1: '先圈出題目裡所有分數，看看分母是否相同。\n📌 相同分母 → 直接算分子；不同 → 先通分。',
      L2: '🖼️ 把兩個分數畫成長條圖，比較包含幾個一樣大的格子。',
      L3: '📊 數每個分數佔幾格 → 加起來佔幾格 → 寫成分數。\n驗證：格數加總 = 全部嗎？',
      L4: '📝 列式：通分後分子做加減 → 約分到最簡。\n✅ 結果介於兩個分數之間嗎？\n🏁 填入你的答案'
    },
    /* ------- 分數文字題 ------- */
    fracWord: {
      L1: '先圈出「全部」「部分」「剩下」，找出要求的量。\n📌 第二段的分數是對哪個量（全部 or 剩下）？',
      L2: '🖼️ 畫一個長條代表全部，用不同顏色標出每一部分。',
      L3: '📊 每一色塊佔全體的多少？加總所有色塊 = 全部嗎？',
      L4: '📝 列式：比例→乘法、反推→除法。\n✅ 把答案代回題目檢查是否合理。\n🏁 填入你的答案'
    },
    /* ------- 分數的分數 / 兩段剩餘 ------- */
    fracRemain: {
      L1: '先圈出每一段的「分數」與「對象」。\n⚠️ 基準量切換：第二次吃的是「剩下的」，不是原本的！\n📌 先想：第一步做完剩多少？第二步是對「剩下」再取分數。',
      L2: '🖼️ 把全體畫成長條 → 切出第一段（直切）→ 在剩下的部分再橫切出第二段。\n🟥 第一段 🟧 第二段 🟦 最後剩下',
      L3: '📊 全部切成小格子 → 數各色格數 → 寫成分數。\n🟥 = ?/?　🟧 = ?/?　🟦 = ?/?\n驗證：🟥 + 🟧 + 🟦 = 全部',
      L4: '📝 分步算式：\n　步驟① 1 − (第一段分數) = 剩下\n　步驟② 剩下 × (第二段分數) = 第二段量\n✅ 第二段 < 剩下？ 全部 > 第二段？\n❌ 常見錯誤：直接用「全部×第二段分數」\n🏁 填入你的答案'
    },
    /* ------- 小數運算 ------- */
    decimal: {
      L1: '先圈出每個小數的位數（幾位小數）。\n📌 估算：答案應該比原數大還是小？',
      L2: '🖼️ 在數線上標出每個小數的位置，看相對大小。',
      L3: '📊 把小數寫成分數形式再對齊，讀出每一位的值。',
      L4: '📝 先當整數算 → 再放回小數點（位數加總）。\n✅ 用整數近似值檢查量級是否合理。\n🏁 填入你的答案'
    },
    /* ------- 百分率 / 折扣 ------- */
    percent: {
      L1: '先圈出「原量」「百分率/折扣率」「求什麼」。\n📌 百分率 → 倍率：p% = p/100，x折 = x/10。',
      L2: '🖼️ 想像 100 格方格紙，塗滿百分比對應的格數。',
      L3: '📊 數塗色格子佔 100 格的多少 → 對應百分比。',
      L4: '📝 列式：求部分 → 原量×倍率；求全體 → 部分÷倍率。\n✅ 打折後 < 原價？增加後 > 原量？\n🏁 填入你的答案'
    },
    /* ------- 時間 ------- */
    time: {
      L1: '先圈出所有時間數值，統一成（時:分）或（分鐘）。\n📌 注意是否跨日/跨午。',
      L2: '🖼️ 在時鐘面上標出起始時間和結束時間。',
      L3: '📊 從起點到終點，數鐘面上走了幾大格（小時）幾小格（分鐘）。',
      L4: '📝 分鐘做運算 → 超過60進位/不夠減借位。\n✅ 結果轉回要求格式，看鐘面是否合理。\n🏁 填入你的答案'
    },
    /* ------- 體積 / 面積 ------- */
    volume: {
      L1: '先圈出長、寬、高（或底、高），確認求面積還是體積。\n📌 面積=平方單位，體積=立方單位。',
      L2: '🖼️ 想像堆積木：底面排好再一層一層往上疊。',
      L3: '📊 數底面幾個 × 疊幾層 = 全部幾個積木。',
      L4: '📝 底面積 = 長×寬 → 體積 = 底面積×高。\n✅ 組合體要拆分成基本形再加減。\n🏁 填入你的答案'
    },
    /* ------- 平均 ------- */
    average: {
      L1: '先圈出「總量」和「分成幾份」。\n📌 平均 = 總量 ÷ 份數。',
      L2: '🖼️ 把所有數據排在一排，想像把高的「削掉」補到低的。',
      L3: '📊 削補完後每一份一樣高 → 那個高度就是平均。',
      L4: '📝 列式：先加總 → 再除以個數。\n✅ 答案應介於最大與最小值之間。\n🏁 填入你的答案'
    },
    /* ------- 通用兜底 ------- */
    generic: {
      L1: '先圈出題目的已知量、未知量與單位。\n📌 想好「對誰做運算」。',
      L2: '🖼️ 把題目的數量關係畫成線段圖或表格。',
      L3: '📊 從圖表中讀出各量之間的關係。',
      L4: '📝 列式：把文字翻成算式，逐步寫清楚。\n✅ 把答案代回去看是否合理，確認單位。\n🏁 填入你的答案'
    }
  };

  /* 題型 → 模板家族 */
  var KIND_TO_FAMILY = {};
  /* fracAdd */
  ['fraction_addsub','add_unlike','sub_unlike','fraction_add_unlike','fraction_sub_mixed','u2_frac_addsub_life','u2_fraction_add_sub','add_like','sub_like','equivalent','simplify'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracAdd'; });
  /* fracWord */
  ['fraction_of_quantity','reverse_fraction','average_division','generic_fraction_word','fraction_mul','mul','u1_avg_fraction','u3_frac_times_int','fraction_times_fraction','int_times_fraction','mul_int','fraction_to_percent'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracWord'; });
  /* fracRemain (two-step remainder) */
  ['remaining_after_fraction','remain_then_fraction','fraction_remaining','remaining_by_fraction','fraction_of_fraction'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracRemain'; });
  /* decimal */
  ['d_mul_d','d_div_int','d_mul_int','int_mul_d','int_div_int_to_decimal','decimal_mul','decimal_div','decimal_times_decimal','x10_shift','u6_frac_dec_convert','u9_unit_convert_decimal','u4_money_decimal_addsub','u5_decimal_muldiv_price','unit_convert','u6_unit_decimal','unit_price','mixed_convert','decimal_times_integer','ratio_add_decimal','decimal_multiplication','liter_to_ml','decimal_to_percent','percent_to_decimal'].forEach(function(k){ KIND_TO_FAMILY[k] = 'decimal'; });
  /* percent */
  ['percent_of','percent_find_whole','percent_increase_decrease','percent_interest','ratio_missing_to_1','ratio_sub_decimal','discount','u7_discount_percent','u8_ratio_recipe','u4_discount_percent','u5_ratio_proportion','percent_discount','percent_find_part','percent_find_percent','percent_meaning','percent_tax_service','percent_to_ppm','ratio_part_total','ratio_remaining','ratio_unit_rate','find_percent','cheng_increase'].forEach(function(k){ KIND_TO_FAMILY[k] = 'percent'; });
  /* time */
  ['time_add','time_add_cross_day','time_sub_cross_day','u10_rate_time_distance','u9_time_trip','clock_angle','time_multiply'].forEach(function(k){ KIND_TO_FAMILY[k] = 'time'; });
  /* volume */
  ['rect_cm3','composite','composite3','rect_find_height','cube_find_edge','cm3_to_m3','m3_to_cm3','surface_area_rect_prism','area_tiling','decimal_dims','mixed_units','volume_rect_prism','u8_area_perimeter','base_area_h','volume_fill','perimeter_fence','cube_cm3','area_trapezoid','surface_area_contact_removed','area_congruent_tile','volume_calculation','ha_to_m2','km2_to_ha','are_to_m2','cm3_to_ml','area_triangle','surface_area_cube','area_parallelogram','area_difference'].forEach(function(k){ KIND_TO_FAMILY[k] = 'volume'; });
  /* average */
  ['shopping_two_step','general','u1_average','temperature_change','u7_speed','make_change','u3_money','buy_many','displacement','proportional_split','table_stats','u10_multi_step','multi_step','division_application'].forEach(function(k){ KIND_TO_FAMILY[k] = 'average'; });

  function getFamily(kind){
    return KIND_TO_FAMILY[String(kind || '')] || 'generic';
  }

  /**
   * Detect if a question is a pure arithmetic expression (no word-problem context).
   * e.g. "（帝國｜分數乘法）2/12 × 5/9 = ？（答案寫最簡分數）" → true
   * e.g. "小明有120顆糖，分給弟弟2/5，還剩多少？" → false
   */
  function isPureCalculation(text){
    var s = String(text || '');
    /* If text contains narrative / word-problem keywords, it's NOT pure calc */
    if (/[有共剩還借送給買賣付找吃喝用出拿走佔]|全部|公[斤升分里尺寸噸]|[小大][明華美英]|[甲乙丙丁]|[一二三四五六七八九十][個人份]|顆|瓶|碗|籃|盒|袋|張|支|塊|條|包|罐|片|杯|瓶|多少|幾|若|如果|請問/.test(s)) return false;
    return true;
  }

  function getTemplate(kind){
    var fam = getFamily(kind);
    return TEMPLATE_MAP[fam] || TEMPLATE_MAP.generic;
  }

  /**
   * getTemplatedHint(question, level) — 四級模板 hint (v2)
   * level: 1=觀念鎖定, 2=畫圖, 3=讀圖得分數, 4=算式收斂+合理性檢查
   * Backward-compat: old 3-level callers map L3→L4.
   */
  function getTemplatedHint(q, level){
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    var tpl = getTemplate(q && q.kind);
    var keys = ['L1','L2','L3','L4'];
    return tpl[keys[lv-1]] || tpl.L1;
  }

  /* ============================================================
   * 2b. SVG Diagram Generators
   * ============================================================ */

  /**
   * buildFractionBarSVG(fracs, colors, width, height)
   * Generates an inline SVG string showing a bar model.
   * fracs: array of {num, den}, e.g. [{num:1,den:5},{num:1,den:3}]
   * Actions: first fraction consumed from whole, second from remainder.
   * For fracRemain: bar is cut vertically first, then horizontally.
   */
  function buildFractionBarSVG(fracs, opts){
    opts = opts || {};
    var W = opts.width  || 320;
    var H = opts.height || 60;
    var colors = opts.colors || ['#ef4444','#f97316','#3b82f6'];
    var labels = opts.labels || [];

    if (!fracs || fracs.length === 0){
      return '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg">' +
             '<rect x="0" y="0" width="'+W+'" height="'+H+'" fill="#374151" rx="4"/>' +
             '<text x="'+W/2+'" y="'+H/2+'" text-anchor="middle" dy=".35em" fill="#9ca3af" font-size="12">（無分數可顯示）</text>' +
             '</svg>';
    }

    var ariaLabel = 'Fraction bar diagram';
    if (fracs.length >= 2) ariaLabel = 'Fraction bar: ' + fracs[0].num+'/'+fracs[0].den + ' then ' + fracs[1].num+'/'+fracs[1].den + ' of remainder';
    else if (fracs.length === 1) ariaLabel = 'Fraction bar: ' + fracs[0].num+'/'+fracs[0].den;
    var svg = '<svg width="'+W+'" height="'+(H+24)+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+ariaLabel+'" style="display:block;margin:6px auto">';

    /* Cross-hatch pattern for consumed portions */
    svg += '<defs>';
    svg += '<pattern id="hatch0" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">';
    svg += '<line x1="0" y1="0" x2="0" y2="6" stroke="'+colors[0]+'" stroke-width="1.5" opacity="0.4"/>';
    svg += '</pattern>';
    svg += '<pattern id="hatch1" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">';
    svg += '<line x1="0" y1="0" x2="0" y2="6" stroke="'+colors[1]+'" stroke-width="1.5" opacity="0.4"/>';
    svg += '</pattern>';
    svg += '</defs>';

    /* Background bar */
    svg += '<rect x="0" y="0" width="'+W+'" height="'+H+'" fill="#374151" rx="4" stroke="#6b7280" stroke-width="1"/>';

    /* For fracRemain: show sequential consumption */
    if (fracs.length >= 2){
      var f1 = fracs[0]; /* first consumed fraction */
      var f2 = fracs[1]; /* second consumed from remainder */
      var den1 = f1.den || 1;
      var num1 = f1.num || 0;
      var den2 = f2.den || 1;
      var num2 = f2.num || 0;

      var totalParts = lcm(den1, den2) || den1 * den2;
      var partW = W / totalParts;

      /* Parts for first fraction */
      var parts1 = totalParts * num1 / den1;
      /* Remaining after first */
      var remaining = totalParts - parts1;
      /* Parts for second fraction (of remainder) */
      var parts2 = remaining * num2 / den2;

      /* Draw grid lines */
      for (var g = 1; g < totalParts; g++){
        svg += '<line x1="'+(g*partW)+'" y1="0" x2="'+(g*partW)+'" y2="'+H+'" stroke="#6b7280" stroke-width="0.5"/>';
      }

      /* Color first fraction (consumed) — solid fill + cross-hatch overlay */
      for (var i = 0; i < Math.round(parts1); i++){
        svg += '<rect x="'+(i*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="'+colors[0]+'" opacity="0.6"/>';
        svg += '<rect x="'+(i*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="url(#hatch0)"/>';
      }

      /* Dashed cut boundary after first consumption */
      var cutX = Math.round(parts1) * partW;
      svg += '<line x1="'+cutX+'" y1="0" x2="'+cutX+'" y2="'+H+'" stroke="#fbbf24" stroke-width="2" stroke-dasharray="4,3"/>';
      svg += '<text x="'+cutX+'" y="-3" text-anchor="middle" fill="#fbbf24" font-size="9">✂ 切</text>';

      /* Color second fraction (consumed from remainder) — solid + cross-hatch */
      var start2 = Math.round(parts1);
      for (var j = 0; j < Math.round(parts2); j++){
        svg += '<rect x="'+((start2+j)*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="'+colors[1]+'" opacity="0.6"/>';
        svg += '<rect x="'+((start2+j)*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="url(#hatch1)"/>';
      }

      /* Remaining is uncolored (or blue) */
      var start3 = start2 + Math.round(parts2);
      for (var k = start3; k < totalParts; k++){
        svg += '<rect x="'+(k*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="'+colors[2]+'" opacity="0.4"/>';
      }

      /* Labels below */
      var lbl1 = labels[0] || ('🟥 '+num1+'/'+den1);
      var lbl2 = labels[1] || ('🟧 '+num2+'/'+den2+' of 剩下');
      var lbl3 = labels[2] || '🟦 最後剩下';
      svg += '<text x="'+(Math.round(parts1)/2*partW)+'" y="'+(H+14)+'" text-anchor="middle" fill="'+colors[0]+'" font-size="11" font-weight="700">'+lbl1+'</text>';
      svg += '<text x="'+((start2+Math.round(parts2)/2)*partW)+'" y="'+(H+14)+'" text-anchor="middle" fill="'+colors[1]+'" font-size="11" font-weight="700">'+lbl2+'</text>';
      if (totalParts - start3 > 0){
        svg += '<text x="'+((start3+(totalParts-start3)/2)*partW)+'" y="'+(H+14)+'" text-anchor="middle" fill="'+colors[2]+'" font-size="11" font-weight="700">'+lbl3+'</text>';
      }
    } else {
      /* Single fraction bar */
      var f = fracs[0];
      var den = f.den || 1;
      var num = f.num || 0;
      var pw = W / den;
      for (var g2 = 1; g2 < den; g2++){
        svg += '<line x1="'+(g2*pw)+'" y1="0" x2="'+(g2*pw)+'" y2="'+H+'" stroke="#6b7280" stroke-width="0.5"/>';
      }
      for (var i2 = 0; i2 < num; i2++){
        svg += '<rect x="'+(i2*pw+0.5)+'" y="0.5" width="'+(pw-1)+'" height="'+(H-1)+'" fill="'+colors[0]+'" opacity="0.7"/>';
      }
      svg += '<text x="'+(W/2)+'" y="'+(H+14)+'" text-anchor="middle" fill="#e5e7eb" font-size="11">'+num+'/'+den+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildGridSVG(rows, cols, colorMap)
   * colorMap: array of {count, color, label}
   * Generates a grid showing fraction decomposition.
   */
  function buildGridSVG(rows, cols, colorMap, opts){
    opts = opts || {};
    var cellSize = opts.cellSize || 24;
    var W = cols * cellSize;
    var H = rows * cellSize;
    var gridAriaLabel = 'Grid diagram ' + rows + ' by ' + cols;
    if (colorMap && colorMap.length > 0) gridAriaLabel += ': ' + colorMap.map(function(c){ return (c.label||c.count+' cells'); }).join(', ');
    var svg = '<svg width="'+(W+2)+'" height="'+(H+30)+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+gridAriaLabel+'" style="display:block;margin:6px auto">';

    /* Draw cells */
    var cellIdx = 0;
    var colorIdx = 0;
    var colorUsed = 0;
    for (var r = 0; r < rows; r++){
      for (var c = 0; c < cols; c++){
        var fill = '#374151';
        if (colorMap && colorIdx < colorMap.length){
          fill = colorMap[colorIdx].color || '#374151';
          colorUsed++;
          if (colorUsed >= colorMap[colorIdx].count){
            colorIdx++;
            colorUsed = 0;
          }
        }
        svg += '<rect x="'+(c*cellSize+1)+'" y="'+(r*cellSize+1)+'" width="'+(cellSize-2)+'" height="'+(cellSize-2)+'" fill="'+fill+'" rx="2" stroke="#6b7280" stroke-width="0.5"/>';
        cellIdx++;
      }
    }

    /* Labels below grid */
    if (colorMap){
      var labelX = 4;
      for (var ci = 0; ci < colorMap.length; ci++){
        var cm = colorMap[ci];
        var total = rows * cols;
        svg += '<rect x="'+labelX+'" y="'+(H+6)+'" width="12" height="12" fill="'+(cm.color||'#374151')+'" rx="2"/>';
        svg += '<text x="'+(labelX+16)+'" y="'+(H+16)+'" fill="#e5e7eb" font-size="10">'+(cm.label || cm.count+'/'+total)+'</text>';
        labelX += 16 + ((cm.label||'').length + 6) * 6;
      }
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildNumberLineSVG(values, highlight)
   * For decimal visualization.
   */
  function buildNumberLineSVG(values, opts){
    opts = opts || {};
    var W = opts.width || 320;
    var H = 50;
    if (!values || values.length === 0) return '';

    var min = Math.floor(Math.min.apply(null, values));
    var max = Math.ceil(Math.max.apply(null, values));
    if (min === max) { min -= 1; max += 1; }
    var range = max - min;

    var nlAriaLabel = 'Number line with values: ' + values.join(', ');
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+nlAriaLabel+'" style="display:block;margin:6px auto">';
    var pad = 20;
    var lineW = W - pad * 2;

    /* Main line */
    svg += '<line x1="'+pad+'" y1="25" x2="'+(W-pad)+'" y2="25" stroke="#9ca3af" stroke-width="2"/>';

    /* Tick marks for integers */
    for (var t = min; t <= max; t++){
      var x = pad + (t - min) / range * lineW;
      svg += '<line x1="'+x+'" y1="20" x2="'+x+'" y2="30" stroke="#9ca3af" stroke-width="1"/>';
      svg += '<text x="'+x+'" y="42" text-anchor="middle" fill="#9ca3af" font-size="10">'+t+'</text>';
    }

    /* Value markers */
    var colors = ['#ef4444','#3b82f6','#22c55e','#f97316'];
    for (var v = 0; v < values.length; v++){
      var vx = pad + (values[v] - min) / range * lineW;
      svg += '<circle cx="'+vx+'" cy="25" r="5" fill="'+(colors[v%colors.length])+'"/>';
      svg += '<text x="'+vx+'" y="14" text-anchor="middle" fill="'+(colors[v%colors.length])+'" font-size="10" font-weight="700">'+values[v]+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildPercentGridSVG(percent)
   * 10x10 grid with colored cells for percentage.
   */
  function buildPercentGridSVG(percent){
    var p = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
    var colorMap = [];
    if (p > 0) colorMap.push({ count: p, color: '#3b82f6', label: p+'%' });
    if (p < 100) colorMap.push({ count: 100 - p, color: '#374151', label: (100-p)+'%' });
    return buildGridSVG(10, 10, colorMap, { cellSize: 16 });
  }

  /**
   * buildPlaceValueSVG(value, opts)
   * Visualizes a decimal number by decomposing it into place-value columns.
   * Each column is a labeled stack: ones, tenths, hundredths, etc.
   * value: number (e.g. 3.14)
   */
  function buildPlaceValueSVG(value, opts){
    opts = opts || {};
    var v = Number(value);
    if (!isFinite(v) || v < 0) return '';

    /* Decompose into integer + decimal digits */
    var parts = String(v).split('.');
    var intPart = parts[0] || '0';
    var decPart = parts[1] || '';

    /* Build columns: each digit with its place name and value */
    var columns = [];
    var placeNames = ['千','百','十','個'];
    /* Pad integer part to at least show '個' */
    var intDigits = intPart.split('');
    var intLen = intDigits.length;
    for (var i = 0; i < intLen; i++){
      var pIdx = placeNames.length - intLen + i;
      var pName = pIdx >= 0 ? placeNames[pIdx] : '';
      columns.push({ digit: intDigits[i], place: pName, val: parseInt(intDigits[i],10) * Math.pow(10, intLen - i - 1) });
    }

    /* Decimal point marker */
    columns.push({ digit: '.', place: '', val: 0, isDot: true });

    /* Decimal digits */
    var decNames = ['十分位','百分位','千分位'];
    for (var d = 0; d < decPart.length && d < 3; d++){
      columns.push({ digit: decPart[d], place: decNames[d], val: parseInt(decPart[d],10) / Math.pow(10, d+1) });
    }

    /* SVG layout */
    var colW = 38;
    var dotW = 14;
    var totalW = 0;
    for (var c = 0; c < columns.length; c++) totalW += columns[c].isDot ? dotW : colW;
    totalW += 12; /* padding */
    var chartH = 80;
    var maxDigit = 9;

    var ariaLabel = 'Place value chart for ' + v;
    var svg = '<svg width="'+totalW+'" height="'+(chartH+36)+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+ariaLabel+'" style="display:block;margin:6px auto">';

    var x = 6;
    var baseY = chartH + 4;
    var barColors = { '千': '#ef4444', '百': '#f97316', '十': '#eab308', '個': '#22c55e', '十分位': '#3b82f6', '百分位': '#8b5cf6', '千分位': '#ec4899' };

    for (var ci = 0; ci < columns.length; ci++){
      var col = columns[ci];
      if (col.isDot){
        svg += '<text x="'+(x+dotW/2)+'" y="'+(baseY-2)+'" text-anchor="middle" fill="#fbbf24" font-size="18" font-weight="900">.</text>';
        x += dotW;
        continue;
      }
      var dv = parseInt(col.digit, 10) || 0;
      var barH = (dv / maxDigit) * (chartH - 16);
      var fillColor = barColors[col.place] || '#6b7280';

      /* Bar */
      if (dv > 0){
        svg += '<rect x="'+x+'" y="'+(baseY-barH)+'" width="'+(colW-4)+'" height="'+barH+'" fill="'+fillColor+'" opacity="0.65" rx="2"/>';
      }

      /* Digit label on bar */
      svg += '<text x="'+(x+(colW-4)/2)+'" y="'+(baseY-barH-3)+'" text-anchor="middle" fill="'+fillColor+'" font-size="12" font-weight="700">'+col.digit+'</text>';

      /* Place name below */
      svg += '<text x="'+(x+(colW-4)/2)+'" y="'+(baseY+12)+'" text-anchor="middle" fill="#9ca3af" font-size="8">'+col.place+'</text>';

      /* Value below place name */
      if (dv > 0){
        var valStr = col.val >= 1 ? String(col.val) : col.val.toFixed(Math.max(1, (col.place.length > 1 ? String(col.val).length - 2 : 1)));
        svg += '<text x="'+(x+(colW-4)/2)+'" y="'+(baseY+24)+'" text-anchor="middle" fill="#6b7280" font-size="7">'+valStr+'</text>';
      }

      x += colW;
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildClockFaceSVG(h, m, opts)
   * Draws an analog clock face with hour/minute hands.
   * h = hours (0-23), m = minutes (0-59).
   * opts.label = text below clock, opts.size = diameter.
   * For time span: pass opts.h2, opts.m2 to draw end-time arc.
   */
  function buildClockFaceSVG(h, m, opts){
    opts = opts || {};
    var S = opts.size || 120;
    var cx = S / 2 + 4;
    var cy = S / 2 + 4;
    var r = S / 2 - 2;
    var totalH = S + 30;
    var label = opts.label || '';

    var clockAriaLabel = 'Clock face showing ' + (h%12||12) + ':' + ('0'+m).slice(-2) + (label ? ' (' + label + ')' : '');
    var svg = '<svg width="'+(S+8)+'" height="'+totalH+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+clockAriaLabel+'" style="display:inline-block;margin:4px 8px;vertical-align:top">';

    /* Clock face circle */
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="#1e293b" stroke="#6b7280" stroke-width="1.5"/>';

    /* Hour markers */
    for (var i = 1; i <= 12; i++){
      var angle = (i * 30 - 90) * Math.PI / 180;
      var tx = cx + (r - 10) * Math.cos(angle);
      var ty = cy + (r - 10) * Math.sin(angle);
      var outerX = cx + (r - 3) * Math.cos(angle);
      var outerY = cy + (r - 3) * Math.sin(angle);
      svg += '<line x1="'+outerX+'" y1="'+outerY+'" x2="'+(cx+(r-7)*Math.cos(angle))+'" y2="'+(cy+(r-7)*Math.sin(angle))+'" stroke="#9ca3af" stroke-width="1.5"/>';
      svg += '<text x="'+tx+'" y="'+ty+'" text-anchor="middle" dy=".35em" fill="#e5e7eb" font-size="'+(r > 50 ? 10 : 8)+'" font-weight="600">'+i+'</text>';
    }

    /* Minute ticks */
    for (var t = 0; t < 60; t++){
      if (t % 5 === 0) continue;
      var ta = (t * 6 - 90) * Math.PI / 180;
      svg += '<line x1="'+(cx+(r-2)*Math.cos(ta))+'" y1="'+(cy+(r-2)*Math.sin(ta))+'" x2="'+(cx+(r-5)*Math.cos(ta))+'" y2="'+(cy+(r-5)*Math.sin(ta))+'" stroke="#4b5563" stroke-width="0.5"/>';
    }

    /* Time span arc (if end time provided) */
    if (opts.h2 !== undefined && opts.m2 !== undefined){
      var startAngle = ((h % 12) * 30 + m * 0.5 - 90) * Math.PI / 180;
      var endAngle = ((opts.h2 % 12) * 30 + opts.m2 * 0.5 - 90) * Math.PI / 180;
      var arcR = r - 16;
      var sx = cx + arcR * Math.cos(startAngle);
      var sy = cy + arcR * Math.sin(startAngle);
      var ex = cx + arcR * Math.cos(endAngle);
      var ey = cy + arcR * Math.sin(endAngle);
      /* Determine large-arc flag */
      var diff = ((opts.h2 % 12) * 60 + opts.m2) - ((h % 12) * 60 + m);
      if (diff < 0) diff += 720;
      var largeArc = diff > 360 ? 1 : 0;
      svg += '<path d="M '+sx+' '+sy+' A '+arcR+' '+arcR+' 0 '+largeArc+' 1 '+ex+' '+ey+'" fill="none" stroke="rgba(59,130,246,.4)" stroke-width="'+(arcR > 30 ? 8 : 5)+'" stroke-linecap="round"/>';
    }

    /* Hour hand */
    var hAngle = ((h % 12) * 30 + m * 0.5 - 90) * Math.PI / 180;
    var hLen = r * 0.5;
    svg += '<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+hLen*Math.cos(hAngle))+'" y2="'+(cy+hLen*Math.sin(hAngle))+'" stroke="#ef4444" stroke-width="3" stroke-linecap="round"/>';

    /* Minute hand */
    var mAngle = (m * 6 - 90) * Math.PI / 180;
    var mLen = r * 0.72;
    svg += '<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+mLen*Math.cos(mAngle))+'" y2="'+(cy+mLen*Math.sin(mAngle))+'" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>';

    /* Center dot */
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="3" fill="#e5e7eb"/>';

    /* Label */
    if (label){
      svg += '<text x="'+cx+'" y="'+(S+16)+'" text-anchor="middle" fill="#e5e7eb" font-size="10" font-weight="600">'+escapeHTML(label)+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * parseVolumeDims(text, kind)
   * Intelligently extract length / width / height from question text.
   * For rect_find_height or similar reverse-solve questions,
   * detects which dimension is unknown and avoids putting volume into height.
   * Returns { l, w, h, vol, area, unit, unknownDim:'h'|'w'|'l'|'edge'|null }
   */
  function parseVolumeDims(text, kind){
    var um = text.match(/公分|cm|公尺|m/);
    var unit = um ? um[0] : '';
    /* Explicit labelled extraction */
    var lm = text.match(/長[是為]?\s*(\d+(?:\.\d+)?)/);
    var wm = text.match(/寬[是為]?\s*(\d+(?:\.\d+)?)/);
    var hm = text.match(/高[是為]?\s*(\d+(?:\.\d+)?)/);
    var vm = text.match(/體積[是為]?\s*(\d+(?:\.\d+)?)/);
    var am = text.match(/面積[是為]?\s*(\d+(?:\.\d+)?)/);
    var em = text.match(/邊長[是為]?\s*(\d+(?:\.\d+)?)/);
    var l = lm ? parseFloat(lm[1]) : 0;
    var w = wm ? parseFloat(wm[1]) : 0;
    var h = hm ? parseFloat(hm[1]) : 0;
    var vol = vm ? parseFloat(vm[1]) : 0;
    var area = am ? parseFloat(am[1]) : 0;
    var edge = em ? parseFloat(em[1]) : 0;
    var unknownDim = null;
    /* Detect reverse-solve type */
    var isFindH = /反求高|高是多少|求高/.test(text) || kind === 'rect_find_height';
    var isFindEdge = /反求邊|邊長是多少|求邊長/.test(text) || kind === 'cube_find_edge';
    if (isFindH && l > 0 && w > 0 && vol > 0 && h === 0){
      h = Math.round(vol / (l * w) * 100) / 100;
      unknownDim = 'h';
    } else if (isFindEdge && vol > 0 && edge === 0){
      edge = Math.round(Math.pow(vol, 1/3));
      l = w = h = edge;
      unknownDim = 'edge';
    }
    /* Fallback: if labelled parse found nothing, use raw ints */
    if (l === 0 && w === 0 && h === 0 && edge === 0){
      var rawInts = extractIntegers(text);
      l = rawInts[0] || 1;
      w = rawInts[1] || 1;
      h = rawInts.length > 2 ? rawInts[2] : 0;
      /* Guard: if h is very large relative to l*w, it is likely the volume */
      if (h > 0 && l > 0 && w > 0 && h > l * w * 2){
        vol = h;
        h = Math.round(vol / (l * w) * 100) / 100;
        unknownDim = 'h';
      }
    }
    return { l: l, w: w, h: h, vol: vol, area: area, edge: edge, unit: unit, unknownDim: unknownDim };
  }

  /**
   * buildIsometricBoxSVG(l, w, h, opts)
   * Draws a 3D isometric rectangular box with clear dimension labels.
   * All three dimensions get colour-coded arrow markers + labels.
   * opts.unit, opts.label, opts.unknownDim ('h'|'w'|'l'|'edge').
   */
  function buildIsometricBoxSVG(l, w, h, opts){
    opts = opts || {};
    var unit = opts.unit || '';
    var unknownDim = opts.unknownDim || null;

    /* Scale to fit in a reasonable SVG */
    var maxDim = Math.max(l, w, h, 1);
    var scale = Math.min(20, 120 / maxDim);
    var sL = Math.max(30, l * scale);
    var sW = Math.max(18, w * scale * 0.5); /* foreshortened */
    var sH = Math.max(30, h * scale);

    /* Isometric offsets */
    var ofsX = sW * 0.866; /* cos(30) */
    var ofsY = sW * 0.5;   /* sin(30) */

    /* Padding for labels */
    var leftPad = 80;
    var rightPad = 80;
    var bx = leftPad;
    var W = Math.ceil(bx + sL + ofsX + rightPad);
    var H = Math.ceil(sH + ofsY + 50);
    var by = sH + 16;

    /* Build label texts */
    var uSfx = unit ? ' ' + unit : '';
    var hText = unknownDim === 'h' ? '高 = ?' : ('高 ' + h + uSfx);
    var lText = unknownDim === 'l' ? '長 = ?' : ('長 ' + l + uSfx);
    var wText = unknownDim === 'w' ? '寬 = ?' : ('寬 ' + w + uSfx);
    if (unknownDim === 'edge'){
      hText = '邊長 = ?'; lText = '邊長 = ?'; wText = '邊長 = ?';
    }

    var boxAriaLabel = 'Isometric box: length ' + l + ', width ' + w + ', height ' + h + uSfx;
    var svg = '<svg width="' + W + '" height="' + (H + 20) + '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' + boxAriaLabel + '" style="display:block;margin:6px auto">';

    /* Arrow marker defs — unique IDs per colour */
    svg += '<defs>';
    svg += '<marker id="arr_r_s" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#ef4444"/></marker>';
    svg += '<marker id="arr_r_e" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M6,0 L0,3 L6,6" fill="#ef4444"/></marker>';
    svg += '<marker id="arr_b_s" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#3b82f6"/></marker>';
    svg += '<marker id="arr_b_e" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M6,0 L0,3 L6,6" fill="#3b82f6"/></marker>';
    svg += '<marker id="arr_g_s" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#22c55e"/></marker>';
    svg += '<marker id="arr_g_e" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M6,0 L0,3 L6,6" fill="#22c55e"/></marker>';
    svg += '</defs>';

    /* Front face */
    svg += '<polygon points="' +
      bx + ',' + by + ' ' + (bx + sL) + ',' + by + ' ' + (bx + sL) + ',' + (by - sH) + ' ' + bx + ',' + (by - sH) +
      '" fill="rgba(59,130,246,.25)" stroke="#3b82f6" stroke-width="1.5"/>';

    /* Top face */
    svg += '<polygon points="' +
      bx + ',' + (by - sH) + ' ' + (bx + sL) + ',' + (by - sH) + ' ' + (bx + sL + ofsX) + ',' + (by - sH - ofsY) + ' ' + (bx + ofsX) + ',' + (by - sH - ofsY) +
      '" fill="rgba(59,130,246,.15)" stroke="#3b82f6" stroke-width="1"/>';

    /* Right side face */
    svg += '<polygon points="' +
      (bx + sL) + ',' + by + ' ' + (bx + sL) + ',' + (by - sH) + ' ' + (bx + sL + ofsX) + ',' + (by - sH - ofsY) + ' ' + (bx + sL + ofsX) + ',' + (by - ofsY) +
      '" fill="rgba(59,130,246,.10)" stroke="#3b82f6" stroke-width="1"/>';

    /* ── Length: arrow + label (bottom of front face, blue) ── */
    var lenY = by + 8;
    svg += '<line x1="' + (bx + 2) + '" y1="' + lenY + '" x2="' + (bx + sL - 2) + '" y2="' + lenY + '" stroke="#3b82f6" stroke-width="1.5" marker-start="url(#arr_b_s)" marker-end="url(#arr_b_e)"/>';
    svg += '<text x="' + (bx + sL / 2) + '" y="' + (lenY + 14) + '" text-anchor="middle" fill="#3b82f6" font-size="12" font-weight="700">' + escapeHTML(lText) + '</text>';

    /* ── Height: arrow + label (left side, red) ── */
    var arrowX = bx - 14;
    svg += '<line x1="' + arrowX + '" y1="' + (by - 2) + '" x2="' + arrowX + '" y2="' + (by - sH + 2) + '" stroke="#ef4444" stroke-width="1.5" marker-start="url(#arr_r_s)" marker-end="url(#arr_r_e)"/>';
    svg += '<text x="' + (arrowX - 4) + '" y="' + (by - sH / 2 + 4) + '" text-anchor="end" fill="#ef4444" font-size="12" font-weight="700">' + escapeHTML(hText) + '</text>';

    /* ── Width: arrow + label (top-right isometric edge, green) ── */
    var wX1 = bx + sL + 2;
    var wY1 = by - sH - 1;
    var wX2 = bx + sL + ofsX - 2;
    var wY2 = by - sH - ofsY + 1;
    svg += '<line x1="' + wX1 + '" y1="' + wY1 + '" x2="' + wX2 + '" y2="' + wY2 + '" stroke="#22c55e" stroke-width="1.5" marker-start="url(#arr_g_s)" marker-end="url(#arr_g_e)"/>';
    var wLabelX = (wX1 + wX2) / 2 + 8;
    var wLabelY = (wY1 + wY2) / 2 - 6;
    svg += '<text x="' + wLabelX + '" y="' + wLabelY + '" fill="#22c55e" font-size="12" font-weight="700">' + escapeHTML(wText) + '</text>';

    /* Optional label */
    if (opts.label){
      svg += '<text x="' + (W / 2) + '" y="' + (H + 14) + '" text-anchor="middle" fill="#9ca3af" font-size="10">' + escapeHTML(opts.label) + '</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildLevelingSVG(values, opts)
   * Bar chart with "leveling" line showing the average.
   * Used for average/平均 questions.
   * values: array of numbers. opts.labels, opts.unit.
   */
  function buildLevelingSVG(values, opts){
    opts = opts || {};
    if (!values || values.length === 0) return '';
    var unit = opts.unit || '';
    var labels = opts.labels || [];
    var maxV = Math.max.apply(null, values);
    var minV = Math.min.apply(null, values);
    if (maxV === 0) maxV = 1;
    var avg = values.reduce(function(s,v){ return s+v; }, 0) / values.length;

    var barW = 28;
    var gap = 8;
    var W = values.length * (barW + gap) + gap + 40;
    var chartH = 100;
    var topPad = 12;
    var H = chartH + topPad + 32;

    var lvlAriaLabel = 'Bar chart showing leveling (average) of ' + values.length + ' values, average = ' + Math.round(avg*100)/100;
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+lvlAriaLabel+'" style="display:block;margin:6px auto">';

    var colors = ['#ef4444','#3b82f6','#22c55e','#f97316','#a855f7','#06b6d4'];

    for (var i = 0; i < values.length; i++){
      var bh = (values[i] / maxV) * chartH;
      var x = gap + i * (barW + gap);
      var y = topPad + chartH - bh;
      var c = colors[i % colors.length];

      /* Bar */
      svg += '<rect x="'+x+'" y="'+y+'" width="'+barW+'" height="'+bh+'" fill="'+c+'" opacity="0.7" rx="2"/>';

      /* Value on top */
      svg += '<text x="'+(x+barW/2)+'" y="'+(y-2)+'" text-anchor="middle" fill="'+c+'" font-size="9" font-weight="700">'+values[i]+'</text>';

      /* If above avg, draw downward hatch (削) */
      if (values[i] > avg){
        var cutH = ((values[i] - avg) / maxV) * chartH;
        svg += '<rect x="'+x+'" y="'+y+'" width="'+barW+'" height="'+Math.round(cutH)+'" fill="url(#hatchAvgCut)" opacity="0.5"/>';
      }

      /* Label below */
      var lbl = labels[i] || String.fromCharCode(65 + i);
      svg += '<text x="'+(x+barW/2)+'" y="'+(topPad+chartH+14)+'" text-anchor="middle" fill="#9ca3af" font-size="9">'+escapeHTML(lbl)+'</text>';
    }

    /* Average line */
    var avgY = topPad + chartH - (avg / maxV) * chartH;
    svg += '<line x1="0" y1="'+avgY+'" x2="'+(W-40)+'" y2="'+avgY+'" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="4,3"/>';
    svg += '<text x="'+(W-38)+'" y="'+(avgY+4)+'" fill="#fbbf24" font-size="9" font-weight="700">平均</text>';

    /* Hatch pattern for cut */
    svg += '<defs><pattern id="hatchAvgCut" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">';
    svg += '<line x1="0" y1="0" x2="0" y2="4" stroke="#fbbf24" stroke-width="1" opacity="0.6"/>';
    svg += '</pattern></defs>';

    svg += '</svg>';
    return svg;
  }

  /**
   * buildNumberBondSVG(parts, whole, opts)
   * Number bond diagram: whole at top, parts fanning out below.
   * Used for generic/multi-step problems.
   */
  function buildNumberBondSVG(parts, whole, opts){
    opts = opts || {};
    if (!parts || parts.length === 0) return '';
    var W = Math.max(200, parts.length * 70 + 40);
    var H = 90;

    var nbAriaLabel = 'Number bond: ' + (whole !== undefined ? whole : '?') + ' splits into ' + parts.join(', ');
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+nbAriaLabel+'" style="display:block;margin:6px auto">';

    /* Whole circle at top center */
    var cx = W / 2;
    var cy = 22;
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="18" fill="rgba(88,166,255,.2)" stroke="#58a6ff" stroke-width="1.5"/>';
    svg += '<text x="'+cx+'" y="'+cy+'" text-anchor="middle" dy=".35em" fill="#58a6ff" font-size="11" font-weight="700">'+(whole !== undefined ? escapeHTML(String(whole)) : '?')+'</text>';

    /* Parts circles below, fanning out */
    var pColors = ['#ef4444','#3b82f6','#22c55e','#f97316','#a855f7'];
    var spacing = Math.min(70, (W - 40) / parts.length);
    var startX = cx - (parts.length - 1) * spacing / 2;
    var py = 68;

    for (var i = 0; i < parts.length; i++){
      var px = startX + i * spacing;
      var pc = pColors[i % pColors.length];

      /* Line from whole to part */
      svg += '<line x1="'+cx+'" y1="'+(cy+18)+'" x2="'+px+'" y2="'+(py-14)+'" stroke="#6b7280" stroke-width="1"/>';

      /* Part circle */
      svg += '<circle cx="'+px+'" cy="'+py+'" r="14" fill="rgba('+hexToRgb(pc)+',.15)" stroke="'+pc+'" stroke-width="1.5"/>';
      svg += '<text x="'+px+'" y="'+py+'" text-anchor="middle" dy=".35em" fill="'+pc+'" font-size="10" font-weight="700">'+escapeHTML(String(parts[i]))+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  function hexToRgb(hex){
    var h = hex.replace('#','');
    return parseInt(h.substr(0,2),16)+','+parseInt(h.substr(2,2),16)+','+parseInt(h.substr(4,2),16);
  }

  /**
   * buildComparisonBarSVG(items, opts)
   * Horizontal bar comparison chart.
   * items: array of {label, value, color?}
   * Useful for comparing quantities (原價 vs 折後, 兩人各自的量, etc.)
   */
  /**
   * buildFractionCircleSVG(fracs, opts)
   * Draws a pie-chart circle showing fraction parts of a whole.
   * fracs: array of { num, den, label?, color? }
   * Great for "part of a whole" intuition.
   */
  function buildFractionCircleSVG(fracs, opts){
    opts = opts || {};
    if (!fracs || fracs.length === 0) return '';
    var R = opts.radius || 60;
    var cx = R + 4;
    var cy = R + 4;
    var W = (R + 4) * 2 + 100; /* extra space for legend */
    var H = (R + 4) * 2 + 4;

    var defColors = ['#ef4444','#f97316','#3b82f6','#22c55e','#8b5cf6','#ec4899'];
    var ariaFragments = [];
    for (var a = 0; a < fracs.length; a++){
      ariaFragments.push((fracs[a].label || fracs[a].num+'/'+fracs[a].den));
    }
    var ariaLabel = 'Fraction circle diagram: ' + ariaFragments.join(', ');
    var svg = '<svg width="'+W+'" height="'+Math.max(H, fracs.length*22+10)+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+ariaLabel+'" style="display:block;margin:6px auto">';

    /* Background circle */
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="'+R+'" fill="#374151" stroke="#6b7280" stroke-width="1"/>';

    /* Draw sectors */
    var startAngle = -Math.PI / 2; /* Start from top */
    var totalFrac = 0;
    for (var i = 0; i < fracs.length; i++){
      var f = fracs[i];
      var frac = (f.den > 0) ? (f.num / f.den) : 0;
      totalFrac += frac;
    }
    /* Remaining fraction (unfilled portion of circle) */
    var remaining = Math.max(0, 1 - totalFrac);
    var angle = startAngle;

    for (var j = 0; j < fracs.length; j++){
      var fj = fracs[j];
      var fracVal = (fj.den > 0) ? (fj.num / fj.den) : 0;
      if (fracVal <= 0) continue;
      var sweep = fracVal * 2 * Math.PI;
      var endAngle = angle + sweep;
      var largeArc = sweep > Math.PI ? 1 : 0;

      var x1 = cx + R * Math.cos(angle);
      var y1 = cy + R * Math.sin(angle);
      var x2 = cx + R * Math.cos(endAngle);
      var y2 = cy + R * Math.sin(endAngle);

      var color = fj.color || defColors[j % defColors.length];
      svg += '<path d="M'+cx+','+cy+' L'+x1.toFixed(2)+','+y1.toFixed(2)+' A'+R+','+R+' 0 '+largeArc+',1 '+x2.toFixed(2)+','+y2.toFixed(2)+' Z" fill="'+color+'" opacity="0.7" stroke="#1f2937" stroke-width="1"/>';

      angle = endAngle;
    }

    /* Remaining wedge stays as background */

    /* Legend on the right side */
    var legendX = (R + 4) * 2 + 10;
    for (var k = 0; k < fracs.length; k++){
      var fk = fracs[k];
      var ly = 14 + k * 22;
      var lColor = fk.color || defColors[k % defColors.length];
      var lLabel = fk.label || (fk.num + '/' + fk.den);
      svg += '<rect x="'+legendX+'" y="'+(ly-6)+'" width="12" height="12" fill="'+lColor+'" rx="2"/>';
      svg += '<text x="'+(legendX+16)+'" y="'+ly+'" dy=".35em" fill="#e5e7eb" font-size="10">'+escapeHTML(lLabel)+'</text>';
    }
    if (remaining > 0.001){
      var ly2 = 14 + fracs.length * 22;
      svg += '<rect x="'+legendX+'" y="'+(ly2-6)+'" width="12" height="12" fill="#374151" stroke="#6b7280" stroke-width="0.5" rx="2"/>';
      svg += '<text x="'+(legendX+16)+'" y="'+ly2+'" dy=".35em" fill="#9ca3af" font-size="10">剩餘 '+Math.round(remaining*100)+'%</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildTreeDiagramSVG(root, children, opts)
   * Tree breakdown diagram: a root node splits into child nodes.
   * root: { label, value? }
   * children: [{ label, value?, color? }, ...]
   * Good for showing how "全部" breaks into parts in multi-step problems.
   */
  function buildTreeDiagramSVG(root, children, opts){
    opts = opts || {};
    if (!root || !children || children.length === 0) return '';
    var nodeW = 72;
    var nodeH = 28;
    var gapX = 16;
    var gapY = 40;
    var totalChildW = children.length * nodeW + (children.length - 1) * gapX;
    var W = Math.max(totalChildW + 24, nodeW + 24);
    var H = nodeH + gapY + nodeH + 30;
    var rootX = W / 2;
    var rootY = 16;
    var defColors = ['#ef4444','#f97316','#3b82f6','#22c55e','#8b5cf6'];

    var ariaLabel = 'Tree diagram: ' + (root.label || 'whole') + ' splits into ' + children.map(function(c){ return c.label; }).join(', ');
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+escapeHTML(ariaLabel)+'" style="display:block;margin:6px auto">';

    /* Root node */
    svg += '<rect x="'+(rootX - nodeW/2)+'" y="'+rootY+'" width="'+nodeW+'" height="'+nodeH+'" fill="#1f2937" stroke="#9ca3af" stroke-width="1" rx="6"/>';
    var rootText = root.label || '全部';
    if (root.value !== undefined) rootText += ' ' + root.value;
    svg += '<text x="'+rootX+'" y="'+(rootY + nodeH/2)+'" text-anchor="middle" dy=".35em" fill="#e5e7eb" font-size="10" font-weight="700">'+escapeHTML(rootText)+'</text>';

    /* Child nodes + connecting lines */
    var childStartX = (W - totalChildW) / 2 + nodeW / 2;
    var childY = rootY + nodeH + gapY;
    for (var i = 0; i < children.length; i++){
      var cx = childStartX + i * (nodeW + gapX);
      var color = children[i].color || defColors[i % defColors.length];

      /* Line from root bottom to child top */
      svg += '<line x1="'+rootX+'" y1="'+(rootY + nodeH)+'" x2="'+cx+'" y2="'+childY+'" stroke="'+color+'" stroke-width="1.5" opacity="0.6"/>';

      /* Child node */
      svg += '<rect x="'+(cx - nodeW/2)+'" y="'+childY+'" width="'+nodeW+'" height="'+nodeH+'" fill="'+color+'" opacity="0.2" stroke="'+color+'" stroke-width="1" rx="6"/>';
      var childText = children[i].label || '';
      if (children[i].value !== undefined) childText += ' ' + children[i].value;
      svg += '<text x="'+cx+'" y="'+(childY + nodeH/2)+'" text-anchor="middle" dy=".35em" fill="'+color+'" font-size="9" font-weight="700">'+escapeHTML(childText)+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildAreaModelSVG(length, width, opts)
   * Rectangular area model — shows a rectangle divided into sub-regions.
   * Useful for multiplication (including fraction multiplication).
   * opts.partitions: [{ label, fraction, color }] — vertical partitions of the rectangle
   */
  /**
   * buildTapeModelSVG(segments, opts)
   * A tape (number strip) diagram showing sequential segments.
   * segments: [{ label, fraction?, value?, color? }]
   * Total of all fractions should sum to 1 (whole).
   * Great for part-part-whole decomposition.
   */
  function buildTapeModelSVG(segments, opts){
    opts = opts || {};
    if (!segments || segments.length === 0) return '';
    var W = opts.width || 300;
    var tapeH = 36;
    var pad = 8;
    var H = tapeH + 44;
    var defColors = ['#ef4444','#f97316','#3b82f6','#22c55e','#8b5cf6','#ec4899'];

    /* Calculate total to normalize */
    var totalFrac = 0;
    for (var i = 0; i < segments.length; i++){
      totalFrac += segments[i].fraction || (1 / segments.length);
    }
    if (totalFrac === 0) totalFrac = 1;

    var ariaFragments = segments.map(function(s){ return s.label || ''; });
    var ariaLabel = 'Tape model: ' + ariaFragments.join(', ');
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+escapeHTML(ariaLabel)+'" style="display:block;margin:6px auto">';

    /* Background tape */
    svg += '<rect x="'+pad+'" y="'+pad+'" width="'+(W - pad*2)+'" height="'+tapeH+'" fill="#374151" stroke="#6b7280" stroke-width="1" rx="4"/>';

    /* Draw segments */
    var x = pad;
    var tapeW = W - pad * 2;
    for (var j = 0; j < segments.length; j++){
      var seg = segments[j];
      var frac = (seg.fraction || (1 / segments.length)) / totalFrac;
      var sw = Math.round(frac * tapeW);
      var color = seg.color || defColors[j % defColors.length];

      /* Segment fill */
      svg += '<rect x="'+x+'" y="'+pad+'" width="'+sw+'" height="'+tapeH+'" fill="'+color+'" opacity="0.5" rx="'+(j===0?4:0)+'" />';

      /* Segment border */
      if (j > 0){
        svg += '<line x1="'+x+'" y1="'+pad+'" x2="'+x+'" y2="'+(pad+tapeH)+'" stroke="#e5e7eb" stroke-width="1.5"/>';
      }

      /* Label inside segment */
      var labelText = seg.label || '';
      if (sw > 30){
        svg += '<text x="'+(x + sw/2)+'" y="'+(pad + tapeH/2)+'" text-anchor="middle" dy=".35em" fill="#e5e7eb" font-size="9" font-weight="700">'+escapeHTML(labelText)+'</text>';
      }

      /* Value below segment */
      if (seg.value !== undefined){
        svg += '<text x="'+(x + sw/2)+'" y="'+(pad + tapeH + 14)+'" text-anchor="middle" fill="'+color+'" font-size="9" font-weight="700">'+escapeHTML(String(seg.value))+'</text>';
      }

      x += sw;
    }

    /* Total bracket below */
    svg += '<line x1="'+pad+'" y1="'+(pad+tapeH+22)+'" x2="'+(W-pad)+'" y2="'+(pad+tapeH+22)+'" stroke="#9ca3af" stroke-width="1"/>';
    svg += '<text x="'+(W/2)+'" y="'+(pad+tapeH+36)+'" text-anchor="middle" fill="#9ca3af" font-size="10">全部</text>';

    svg += '</svg>';
    return svg;
  }

  /**
   * buildFractionComparisonSVG(frac1, frac2, opts)
   * Side-by-side fraction bars with comparison symbol (>, <, =).
   * frac1/frac2: {num, den}   opts: {width, height}
   */
  function buildFractionComparisonSVG(frac1, frac2, opts){
    opts = opts || {};
    if (!frac1 || !frac2 || !frac1.den || !frac2.den) return '';
    var W = opts.width || 300;
    var barH = 28;
    var gap = 36;
    var pad = 8;
    var barW = (W - gap - pad * 2) / 2;
    var H = barH + 40 + pad * 2;

    var val1 = frac1.num / frac1.den;
    var val2 = frac2.num / frac2.den;
    var cmp = val1 > val2 ? '>' : (val1 < val2 ? '<' : '=');

    var ariaLabel = frac1.num + '/' + frac1.den + ' ' + cmp + ' ' + frac2.num + '/' + frac2.den;
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Fraction comparison: '+escapeHTML(ariaLabel)+'" style="display:block;margin:6px auto">';

    /* Helper: draw one fraction bar */
    function drawBar(x, y, w, h, frac, color){
      var cells = Math.min(frac.den, 20);
      var cellW = w / cells;
      var fillCount = Math.min(Math.round(frac.num * cells / frac.den), cells);
      var s = '';
      /* Background */
      s += '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" fill="#374151" rx="4" stroke="#6b7280" stroke-width="1"/>';
      /* Grid lines */
      for (var i = 1; i < cells; i++){
        s += '<line x1="'+(x + i*cellW)+'" y1="'+y+'" x2="'+(x + i*cellW)+'" y2="'+(y+h)+'" stroke="#6b7280" stroke-width="0.5"/>';
      }
      /* Filled cells */
      for (var j = 0; j < fillCount; j++){
        s += '<rect x="'+(x + j*cellW + 0.5)+'" y="'+(y+0.5)+'" width="'+(cellW-1)+'" height="'+(h-1)+'" fill="'+color+'" opacity="0.6" rx="2"/>';
      }
      /* Label below */
      s += '<text x="'+(x + w/2)+'" y="'+(y + h + 14)+'" text-anchor="middle" fill="'+color+'" font-size="11" font-weight="700">'+frac.num+'/'+frac.den+'</text>';
      return s;
    }

    svg += drawBar(pad, pad, barW, barH, frac1, '#ef4444');
    svg += drawBar(pad + barW + gap, pad, barW, barH, frac2, '#3b82f6');

    /* Comparison symbol in the middle */
    var midX = pad + barW + gap / 2;
    var midY = pad + barH / 2;
    svg += '<text x="'+midX+'" y="'+midY+'" text-anchor="middle" dy=".35em" fill="#e5e7eb" font-size="18" font-weight="700">'+cmp+'</text>';

    svg += '</svg>';
    return svg;
  }

  function buildAreaModelSVG(length, width, opts){
    opts = opts || {};
    var l = (length !== undefined && length !== null) ? Number(length) : 0;
    var w = (width !== undefined && width !== null) ? Number(width) : 0;
    if (!isFinite(l) || !isFinite(w) || l <= 0 || w <= 0) return '';
    var scale = opts.scale || 40;
    var maxDim = 6;
    var drawL = Math.min(l, maxDim) * scale;
    var drawW = Math.min(w, maxDim) * scale;
    var pad = 30;
    var W = drawL + pad * 2 + 20;
    var H = drawW + pad * 2 + 20;
    var partitions = opts.partitions || [];

    var ariaLabel = 'Area model: ' + l + ' x ' + w;
    if (partitions.length > 0) ariaLabel += ' with ' + partitions.length + ' regions';
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+escapeHTML(ariaLabel)+'" style="display:block;margin:6px auto">';

    /* Main rectangle */
    svg += '<rect x="'+pad+'" y="'+pad+'" width="'+drawL+'" height="'+drawW+'" fill="#374151" stroke="#9ca3af" stroke-width="1.5" rx="2"/>';

    /* Partitions (vertical divisions) */
    if (partitions.length > 0){
      var px = pad;
      var defCols = ['#ef4444','#3b82f6','#22c55e','#f97316','#8b5cf6'];
      for (var i = 0; i < partitions.length; i++){
        var part = partitions[i];
        var frac = part.fraction || (1 / partitions.length);
        var pw = frac * drawL;
        var color = part.color || defCols[i % defCols.length];
        svg += '<rect x="'+px+'" y="'+pad+'" width="'+Math.round(pw)+'" height="'+drawW+'" fill="'+color+'" opacity="0.3" stroke="'+color+'" stroke-width="0.5"/>';
        /* Label inside partition */
        svg += '<text x="'+(px + Math.round(pw)/2)+'" y="'+(pad + drawW/2)+'" text-anchor="middle" dy=".35em" fill="'+color+'" font-size="10" font-weight="700">'+escapeHTML(part.label || '')+'</text>';
        px += Math.round(pw);
      }
    }

    /* Dimension labels */
    svg += '<text x="'+(pad + drawL/2)+'" y="'+(pad - 8)+'" text-anchor="middle" fill="#e5e7eb" font-size="11" font-weight="700">'+l+'</text>';
    svg += '<text x="'+(pad - 10)+'" y="'+(pad + drawW/2)+'" text-anchor="middle" dy=".35em" fill="#e5e7eb" font-size="11" font-weight="700" transform="rotate(-90 '+(pad-10)+' '+(pad+drawW/2)+')">'+w+'</text>';

    /* Grid lines for integer grid */
    if (l <= maxDim && w <= maxDim && l === Math.floor(l) && w === Math.floor(w)){
      for (var gx = 1; gx < l; gx++){
        svg += '<line x1="'+(pad + gx*scale)+'" y1="'+pad+'" x2="'+(pad + gx*scale)+'" y2="'+(pad + drawW)+'" stroke="#6b7280" stroke-width="0.5" stroke-dasharray="3,3"/>';
      }
      for (var gy = 1; gy < w; gy++){
        svg += '<line x1="'+pad+'" y1="'+(pad + gy*scale)+'" x2="'+(pad + drawL)+'" y2="'+(pad + gy*scale)+'" stroke="#6b7280" stroke-width="0.5" stroke-dasharray="3,3"/>';
      }
      /* Unit count */
      svg += '<text x="'+(pad + drawL + 6)+'" y="'+(pad + drawW + 12)+'" fill="#9ca3af" font-size="9">= '+(l*w)+' 格</text>';
    }

    svg += '</svg>';
    return svg;
  }

  function buildComparisonBarSVG(items, opts){
    opts = opts || {};
    if (!items || items.length === 0) return '';
    var W = opts.width || 280;
    var barH = 20;
    var gap = 8;
    var labelW = 50;
    var H = items.length * (barH + gap) + gap + 4;
    var maxVal = 0;
    for (var i = 0; i < items.length; i++){
      if (items[i].value > maxVal) maxVal = items[i].value;
    }
    if (maxVal === 0) maxVal = 1;
    var barAreaW = W - labelW - 40;

    var ariaLabel = 'Comparison bar chart: ' + items.map(function(it){ return it.label + '=' + it.value; }).join(', ');
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+ariaLabel+'" style="display:block;margin:6px auto">';

    var defColors = ['#3b82f6','#ef4444','#22c55e','#f97316','#8b5cf6'];
    for (var j = 0; j < items.length; j++){
      var it = items[j];
      var y = gap + j * (barH + gap);
      var bw = (it.value / maxVal) * barAreaW;
      var c = it.color || defColors[j % defColors.length];

      /* Label */
      svg += '<text x="'+(labelW-4)+'" y="'+(y+barH/2)+'" text-anchor="end" dy=".35em" fill="#e5e7eb" font-size="10">'+escapeHTML(it.label)+'</text>';
      /* Bar */
      svg += '<rect x="'+labelW+'" y="'+y+'" width="'+Math.round(bw)+'" height="'+barH+'" fill="'+c+'" opacity="0.7" rx="3"/>';
      /* Value on bar */
      svg += '<text x="'+(labelW+Math.round(bw)+4)+'" y="'+(y+barH/2)+'" dy=".35em" fill="'+c+'" font-size="10" font-weight="700">'+it.value+'</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /* ============================================================
   * 2c. Rich Hint HTML Builder — per-family parametric hints
   * ============================================================ */

  /**
   * buildProgressRingSVG(percent, opts)
   * Circular progress ring for showing completion/correction rates.
   * percent: 0-100, opts: { size, label, color }
   */
  function buildProgressRingSVG(percent, opts){
    opts = opts || {};
    var pct = Math.max(0, Math.min(100, Number(percent) || 0));
    var size = opts.size || 80;
    var r = (size - 10) / 2;
    var cx = size / 2, cy = size / 2;
    var circ = 2 * Math.PI * r;
    var offset = circ * (1 - pct / 100);
    var color = opts.color || (pct >= 70 ? '#3fb950' : (pct >= 40 ? '#d29922' : '#f85149'));
    var label = opts.label || (pct + '%');

    var ariaLabel = 'Progress: ' + pct + '%' + (opts.label ? ' (' + opts.label + ')' : '');
    var svg = '<svg width="'+size+'" height="'+size+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+escapeHTML(ariaLabel)+'" style="display:inline-block;vertical-align:middle">';
    /* Background ring */
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="none" stroke="#374151" stroke-width="6"/>';
    /* Progress arc */
    svg += '<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="none" stroke="'+color+'" stroke-width="6" stroke-linecap="round" stroke-dasharray="'+circ+'" stroke-dashoffset="'+offset+'" transform="rotate(-90 '+cx+' '+cy+')"/>';
    /* Center text */
    svg += '<text x="'+cx+'" y="'+cy+'" text-anchor="middle" dy=".35em" fill="'+color+'" font-size="'+(size > 60 ? 14 : 10)+'" font-weight="700">'+escapeHTML(label)+'</text>';
    svg += '</svg>';
    return svg;
  }

  /**
   * highlightKeywords(htmlStr)
   * Add colored highlighting to key math concepts in hint text.
   * Input should already be HTML-escaped.
   */
  function highlightKeywords(htmlStr){
    var h = htmlStr;
    /* Fraction keywords */
    h = h.replace(/(通分|約分|最簡|分母|分子|帶分數|假分數|真分數)/g, '<span style="color:#58a6ff;font-weight:800">$1</span>');
    /* Operation keywords */
    h = h.replace(/(加法|減法|乘法|除法|加減|乘除)/g, '<span style="color:#3fb950;font-weight:800">$1</span>');
    /* Base switch / conceptual */
    h = h.replace(/(基準量|剩下|全部|部分|百分率|折扣率|倍率|比率)/g, '<span style="color:#f97316;font-weight:800">$1</span>');
    /* Units */
    h = h.replace(/(平方單位|立方單位|公分|公尺|公升|毫升|平方公分|立方公分)/g, '<span style="color:#d29922;font-weight:700">$1</span>');
    /* Warning markers */
    h = h.replace(/(⚠️[^<]*)/g, '<span style="color:#fbbf24;font-weight:800">$1</span>');
    return h;
  }

  /**
   * buildStepIndicatorSVG(currentLevel)
   * 4-step progress rail showing L1–L4 with current step highlighted.
   */
  /**
   * buildBarChartSVG(values, opts)
   * Horizontal bar chart for comparing numeric data (e.g., average problem data points).
   * values = [{ label: 'Mon', value: 85, color?: '#...' }, ...]
   * opts = { width?, height?, maxBars? }
   */
  function buildBarChartSVG(values, opts){
    if (!values || !values.length) return '';
    opts = opts || {};
    var maxBars = opts.maxBars || 8;
    var items = values.slice(0, maxBars);
    var barH = 18;
    var gap = 4;
    var labelW = 40;
    var W = opts.width || 260;
    var H = items.length * (barH + gap) + gap;
    var maxVal = 0;
    for (var i = 0; i < items.length; i++){
      if (items[i].value > maxVal) maxVal = items[i].value;
    }
    if (maxVal === 0) maxVal = 1;
    var barArea = W - labelW - 10;
    var defaultColors = ['#58a6ff','#3fb950','#d29922','#f85149','#bc8cff','#f97316','#22d3ee','#a78bfa'];

    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Bar chart: '+items.length+' data points" style="display:block;margin:4px auto">';

    for (var b = 0; b < items.length; b++){
      var y = gap + b * (barH + gap);
      var bw = Math.max(2, (items[b].value / maxVal) * barArea);
      var col = items[b].color || defaultColors[b % defaultColors.length];
      /* Label */
      svg += '<text x="'+(labelW - 4)+'" y="'+(y + barH/2)+'" text-anchor="end" dy=".35em" fill="#d1d5db" font-size="9">' + escapeHTML(String(items[b].label || '')) + '</text>';
      /* Bar */
      svg += '<rect x="'+labelW+'" y="'+y+'" width="'+Math.round(bw)+'" height="'+barH+'" rx="3" fill="'+col+'" opacity="0.85"/>';
      /* Value */
      svg += '<text x="'+(labelW + Math.round(bw) + 4)+'" y="'+(y + barH/2)+'" dy=".35em" fill="#e5e7eb" font-size="8" font-weight="600">' + items[b].value + '</text>';
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildDotPlotSVG(values, opts)
   * Dot plot showing distribution of numeric values along a number line.
   * Great for visualizing data spread in statistics/average problems.
   * values = [85, 90, 75, 85, 80, ...]
   * opts = { width?, height?, dotRadius?, color? }
   */
  function buildDotPlotSVG(values, opts){
    if (!values || !values.length) return '';
    opts = opts || {};
    var W = opts.width || 260;
    var H = opts.height || 60;
    var r = opts.dotRadius || 5;
    var color = opts.color || '#58a6ff';
    var minV = values[0], maxV = values[0];
    for (var i = 1; i < values.length; i++){
      if (values[i] < minV) minV = values[i];
      if (values[i] > maxV) maxV = values[i];
    }
    var range = maxV - minV || 1;
    var pad = 30;
    var lineW = W - 2 * pad;
    var lineY = H - 18;

    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Dot plot: '+values.length+' data points from '+minV+' to '+maxV+'" style="display:block;margin:4px auto">';

    /* Axis line */
    svg += '<line x1="'+pad+'" y1="'+lineY+'" x2="'+(W-pad)+'" y2="'+lineY+'" stroke="#6b7280" stroke-width="1"/>';
    /* Min and max labels */
    svg += '<text x="'+pad+'" y="'+(H-2)+'" text-anchor="middle" fill="#9ca3af" font-size="8">'+minV+'</text>';
    svg += '<text x="'+(W-pad)+'" y="'+(H-2)+'" text-anchor="middle" fill="#9ca3af" font-size="8">'+maxV+'</text>';

    /* Count stacks at each position */
    var stacks = {};
    for (var j = 0; j < values.length; j++){
      var k = String(values[j]);
      stacks[k] = (stacks[k] || 0) + 1;
    }

    /* Draw dots */
    for (var val in stacks){
      if (!stacks.hasOwnProperty(val)) continue;
      var numVal = parseFloat(val);
      var x = pad + ((numVal - minV) / range) * lineW;
      var count = stacks[val];
      for (var d = 0; d < count; d++){
        var y = lineY - r - 1 - d * (r * 2 + 2);
        svg += '<circle cx="'+Math.round(x)+'" cy="'+Math.round(y)+'" r="'+r+'" fill="'+color+'" opacity="0.8"/>';
      }
    }

    svg += '</svg>';
    return svg;
  }

  function buildStepIndicatorSVG(currentLevel){
    var lv = Math.max(1, Math.min(4, Number(currentLevel) || 1));
    var W = 240;
    var H = 28;
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Hint progress: step '+lv+' of 4" style="display:block;margin:4px auto">';

    var stepX = [30, 90, 150, 210];
    var stepColors = ['#58a6ff','#3fb950','#d29922','#f85149'];
    var stepLabels = ['L1','L2','L3','L4'];

    /* Rail line */
    svg += '<line x1="'+stepX[0]+'" y1="14" x2="'+stepX[3]+'" y2="14" stroke="#4b5563" stroke-width="2"/>';

    /* Completed rail segments */
    for (var s = 0; s < lv - 1 && s < 3; s++){
      svg += '<line x1="'+stepX[s]+'" y1="14" x2="'+stepX[s+1]+'" y2="14" stroke="'+stepColors[s]+'" stroke-width="2.5"/>';
    }

    /* Step circles */
    for (var i = 0; i < 4; i++){
      var isCurrent = (i + 1 === lv);
      var isPast = (i + 1 < lv);
      var r = isCurrent ? 10 : 7;
      var fill = isPast ? stepColors[i] : (isCurrent ? stepColors[i] : '#374151');
      var strokeC = stepColors[i];
      var strokeW = isCurrent ? 2.5 : 1;
      svg += '<circle cx="'+stepX[i]+'" cy="14" r="'+r+'" fill="'+fill+'" stroke="'+strokeC+'" stroke-width="'+strokeW+'"/>';
      /* Check mark for past steps */
      if (isPast){
        svg += '<text x="'+stepX[i]+'" y="14" text-anchor="middle" dy=".35em" fill="#0d1117" font-size="8" font-weight="900">✓</text>';
      } else {
        svg += '<text x="'+stepX[i]+'" y="14" text-anchor="middle" dy=".35em" fill="'+(isCurrent?'#0d1117':'#9ca3af')+'" font-size="7" font-weight="700">'+stepLabels[i]+'</text>';
      }
    }

    svg += '</svg>';
    return svg;
  }

  /**
   * buildRichHintHTML(q, level)
   * Returns HTML string with SVG diagrams + formatted text for a specific level.
   * q = question object { question, kind, answer, ... }
   */
  function buildRichHintHTML(q, level){
    if (!q) return '';
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    var family = getFamily(q.kind);
    var tpl = getTemplate(q.kind);
    var text = q.question || '';
    var fracs = extractFractions(text);
    var ints = extractIntegers(text);

    var html = '';

    /* Step progress indicator for all levels */
    html += buildStepIndicatorSVG(lv);

    /* --- L1: 觀念鎖定 (all families) — context-specific --- */
    if (lv === 1){
      html += '<div class="he-rich-l1">';

      /* Pure calculation override: show direct calculation concept */
      var pureCalc1 = isPureCalculation(text);
      if (pureCalc1 && (family === 'fracWord' || family === 'fracRemain') && fracs.length >= 1){
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        for (var pci = 0; pci < Math.min(fracs.length, 3); pci++){
          html += (pci > 0 ? '　' : '') + '分數' + (pci+1) + ' = <strong>' + fracs[pci].num + '/' + fracs[pci].den + '</strong>';
        }
        html += '</div>';
        html += highlightKeywords(escapeHTML(tpl.L1).replace(/\n/g, '<br>')
          .replace(/找出「全部」是多少，再看「佔幾分之幾」/, '分數乘法 → 分子×分子，分母×分母，能約分先約分'));
        html += '</div>';
        return html;
      }

      /* Inject question-specific context before the generic template */
      if (family === 'fracRemain' && fracs.length >= 2 && ints.length >= 1){
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        html += '全部 = <strong>' + ints[0] + '</strong><br>';
        html += '先用掉全部的 <strong>' + fracs[0].num + '/' + fracs[0].den + '</strong>，<br>';
        html += '「剩下的」又用掉 <strong>' + fracs[1].num + '/' + fracs[1].den + '</strong>。';
        html += '</div>';
      } else if (family === 'fracWord' && fracs.length >= 1 && ints.length >= 1){
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        html += '全部 = <strong>' + ints[0] + '</strong><br>';
        html += '取其中的 <strong>' + fracs[0].num + '/' + fracs[0].den + '</strong>';
        if (fracs.length >= 2) html += '，再取 <strong>' + fracs[1].num + '/' + fracs[1].den + '</strong>';
        html += '</div>';
      } else if (family === 'fracAdd' && fracs.length >= 2){
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        html += '分數① <strong>' + fracs[0].num + '/' + fracs[0].den + '</strong>　分數② <strong>' + fracs[1].num + '/' + fracs[1].den + '</strong><br>';
        html += '分母' + (fracs[0].den === fracs[1].den ? '相同 → 直接算分子' : '不同 → 需要通分') + '';
        html += '</div>';
      } else if (family === 'percent' && ints.length >= 1){
        var pctM1 = text.match(/(\d+)\s*[%％]/);
        var discM1 = text.match(/(\d+)\s*折/);
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        if (pctM1) html += '百分率 = <strong>' + pctM1[1] + '%</strong>　';
        if (discM1) html += '折扣 = <strong>' + discM1[1] + ' 折</strong>　';
        if (ints.length >= 1) html += '原量 = <strong>' + ints[0] + '</strong>';
        html += '</div>';
      } else if (family === 'volume' && ints.length >= 2){
        var vd1 = parseVolumeDims(text, q.kind);
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        if (vd1.l > 0) html += '長 = <strong>' + vd1.l + '</strong>　';
        if (vd1.w > 0) html += '寬 = <strong>' + vd1.w + '</strong>　';
        if (vd1.unknownDim === 'h') html += '高 = <strong>?</strong>　';
        else if (vd1.h > 0) html += '高 = <strong>' + vd1.h + '</strong>　';
        if (vd1.vol > 0) html += '體積 = <strong>' + vd1.vol + '</strong>';
        html += '</div>';
      } else if (family === 'average' && ints.length >= 2){
        html += '<div style="color:#e5e7eb;font-size:12px;margin-bottom:4px">';
        html += '數據：<strong>' + ints.join(', ') + '</strong>（共 ' + ints.length + ' 個）';
        html += '</div>';
      }

      html += highlightKeywords(escapeHTML(tpl.L1).replace(/\n/g, '<br>'));
      html += '</div>';
      if (family === 'fracRemain' || needsBaseSwitchWarning(text)){
        html += '<div class="he-base-switch">⚠️ 基準量切換：第二次操作不是對「全部」，而是對「前一步剩下的量」。</div>';
      }
      return html;
    }

    /* --- L2: 畫圖 (SVG diagrams) --- */
    if (lv === 2){
      var pureCalc = isPureCalculation(text);

      /* Pure calculation: show simple step-by-step text instead of diagrams */
      if (pureCalc && (family === 'fracRemain' || family === 'fracWord' || family === 'fracAdd') && fracs.length >= 1){
        html += '<div class="he-rich-l2" style="line-height:1.8">';
        if (fracs.length >= 2){
          var fa = fracs[0], fb = fracs[1];
          var isAdd = /加|＋|\+/.test(text);
          var isSub = /減|差|－|\-/.test(text) && !/乘|×/.test(text);
          var isMul = /乘|×/.test(text) || family === 'fracWord';
          if (isMul && !isSub && !isAdd){
            html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 分數乘法計算步驟</div>';
            html += '① 先觀察能否<strong>交叉約分</strong>（左分子和右分母、左分母和右分子）<br>';
            html += '② 分子 × 分子：<strong>' + fa.num + ' × ' + fb.num + '</strong><br>';
            html += '③ 分母 × 分母：<strong>' + fa.den + ' × ' + fb.den + '</strong><br>';
            html += '④ 結果再約分成<strong>最簡分數</strong>';
          } else if (isAdd || isSub){
            var op = isSub ? '減' : '加';
            html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 分數' + op + '法計算步驟</div>';
            if (fa.den !== fb.den){
              html += '① 分母不同 → 先<strong>通分</strong>（找最小公倍數）<br>';
              html += '② 通分後分子做' + op + '法<br>';
            } else {
              html += '① 分母相同 → 直接分子做' + op + '法<br>';
            }
            html += '③ 結果<strong>約分</strong>成最簡分數';
          } else {
            html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 計算步驟</div>';
            html += '① 列出算式：<strong>' + fa.num + '/' + fa.den + ' ○ ' + fb.num + '/' + fb.den + '</strong><br>';
            html += '② 依照運算規則逐步計算<br>';
            html += '③ 最後約分成最簡分數';
          }
        } else {
          html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 計算步驟</div>';
          html += '① 列出算式<br>② 逐步計算<br>③ 約分成最簡分數';
        }
        html += '</div>';
        return html;
      }

      html += '<div class="he-rich-l2">' + highlightKeywords(escapeHTML(tpl.L2).replace(/\n/g, '<br>')) + '</div>';

      if ((family === 'fracRemain' || family === 'fracWord') && fracs.length >= 1){
        /* Detect if fracWord question is actually fraction addition/subtraction */
        var isFracAddition = /一共|合計|總共|相加|加起來|加在一起|共[用吃花走]了|共佔/.test(text);
        var isFracSubtraction = /還剩|剩[下餘]|差多少|差幾|多幾|少幾|比.*多|比.*少/.test(text) && !/剩下的又/.test(text);
        var isFracAddSub = isFracAddition || isFracSubtraction;

        if (isFracAddSub && fracs.length >= 2){
          /* === Fraction addition/subtraction — simple step-by-step === */
          var fadd1 = fracs[0], fadd2 = fracs[1];
          var opZh = isFracSubtraction ? '減' : '加';
          var opSign = isFracSubtraction ? '−' : '+';
          var comDenom = lcm(fadd1.den, fadd2.den) || fadd1.den * fadd2.den;
          var newNum1 = fadd1.num * (comDenom / fadd1.den);
          var newNum2 = fadd2.num * (comDenom / fadd2.den);
          var resultNum = isFracSubtraction ? (newNum1 - newNum2) : (newNum1 + newNum2);
          html += '<div style="padding:10px;background:rgba(88,166,255,0.06);border-radius:8px;margin:6px 0;line-height:2">';
          html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 分數' + opZh + '法步驟</div>';
          html += '① 列式：<strong>' + fadd1.num + '/' + fadd1.den + ' ' + opSign + ' ' + fadd2.num + '/' + fadd2.den + '</strong><br>';
          if (fadd1.den !== fadd2.den){
            html += '② 分母不同 → 找最小公倍數 LCM(' + fadd1.den + ', ' + fadd2.den + ') = <strong>' + comDenom + '</strong><br>';
            html += '③ 通分：<strong>' + newNum1 + '/' + comDenom + ' ' + opSign + ' ' + newNum2 + '/' + comDenom + '</strong><br>';
            html += '④ 分子' + opZh + '法：' + newNum1 + ' ' + opSign + ' ' + newNum2 + ' = <strong>' + resultNum + '</strong><br>';
            html += '⑤ 結果 = <strong>' + resultNum + '/' + comDenom + '</strong>，約分成最簡分數';
          } else {
            html += '② 分母相同 → 直接分子' + opZh + '法<br>';
            html += '③ ' + fadd1.num + ' ' + opSign + ' ' + fadd2.num + ' = <strong>' + resultNum + '</strong><br>';
            html += '④ 結果 = <strong>' + resultNum + '/' + comDenom + '</strong>，約分成最簡分數';
          }
          html += '</div>';
        } else {
          /* Original fracRemain/fracWord bar + pie rendering */
          html += buildFractionBarSVG(fracs);
        /* Step-by-step narration for fracRemain (matching reference example) */
        if (family === 'fracRemain' && fracs.length >= 2){
          var f2a = fracs[0], f2b = fracs[1];
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '① 畫一個長方形代表全部';
          if (ints.length >= 1) html += ' = <strong>' + ints[0] + '</strong>';
          html += '<br>';
          html += '② 用直線切成 <strong>' + f2a.den + '</strong> 等份<br>';
          html += '③ 🟥 塗掉 <strong>' + f2a.num + '</strong> 份 → 第1次用掉 <strong>' + f2a.num + '/' + f2a.den + '</strong><br>';
          html += '④ 剩下 <strong>' + (f2a.den - f2a.num) + '</strong> 份 = <strong>' + (f2a.den - f2a.num) + '/' + f2a.den + '</strong><br>';
          html += '⬇️ 只在「剩下的 <strong>' + (f2a.den - f2a.num) + '</strong> 份」用橫線再切 <strong>' + f2b.den + '</strong> 等份<br>';
          html += '⑤ 🟧 「剩下的 <strong>' + f2b.num + '/' + f2b.den + '</strong>」→ 從小格取出<br>';
          html += '⑥ 🟦 最後剩下的小格';
          html += '</div>';
        }
        /* Supplementary circle diagram for intuitive "part of whole" */
        if (fracs.length <= 3){
          html += '<div style="font-size:10px;color:#9ca3af;margin:2px 0 0 0">▼ 圓餅圖：</div>';
          var circleFrags = [];
          for (var cfi = 0; cfi < fracs.length; cfi++){
            circleFrags.push({ num: fracs[cfi].num, den: fracs[cfi].den, label: fracs[cfi].num+'/'+fracs[cfi].den });
          }
          html += buildFractionCircleSVG(circleFrags);
        }
        } /* end else (original bar+pie for non-addition fracWord) */
      } else if (family === 'fracAdd' && fracs.length >= 1){
        /* Simple text-based step-by-step for fraction add/sub */
        if (fracs.length >= 2){
          var isAddL2 = !/減|差|少|扣/.test(text);
          var opZhA = isAddL2 ? '加' : '減';
          var opSignA = isAddL2 ? '+' : '−';
          var comDenA = lcm(fracs[0].den, fracs[1].den) || fracs[0].den * fracs[1].den;
          var newN1 = fracs[0].num * (comDenA / fracs[0].den);
          var newN2 = fracs[1].num * (comDenA / fracs[1].den);
          var resN = isAddL2 ? (newN1 + newN2) : (newN1 - newN2);
          html += '<div style="padding:10px;background:rgba(88,166,255,0.06);border-radius:8px;margin:6px 0;line-height:2">';
          html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 分數' + opZhA + '法步驟</div>';
          html += '① 列式：<strong>' + fracs[0].num + '/' + fracs[0].den + ' ' + opSignA + ' ' + fracs[1].num + '/' + fracs[1].den + '</strong><br>';
          if (fracs[0].den !== fracs[1].den){
            html += '② 分母不同 → 找最小公倍數 LCM(' + fracs[0].den + ', ' + fracs[1].den + ') = <strong>' + comDenA + '</strong><br>';
            html += '③ 通分：<strong>' + newN1 + '/' + comDenA + ' ' + opSignA + ' ' + newN2 + '/' + comDenA + '</strong><br>';
            html += '④ 分子' + opZhA + '法：' + newN1 + ' ' + opSignA + ' ' + newN2 + ' = <strong>' + resN + '</strong><br>';
            html += '⑤ 結果 = <strong>' + resN + '/' + comDenA + '</strong>，約分成最簡分數';
          } else {
            html += '② 分母相同 → 直接分子' + opZhA + '法<br>';
            html += '③ ' + fracs[0].num + ' ' + opSignA + ' ' + fracs[1].num + ' = <strong>' + resN + '</strong><br>';
            html += '④ 結果 = <strong>' + resN + '/' + comDenA + '</strong>，約分成最簡分數';
          }
          html += '</div>';
        } else {
          /* Single fraction — minimal guidance */
          html += '<div style="padding:10px;background:rgba(88,166,255,0.06);border-radius:8px;margin:6px 0;line-height:2">';
          html += '<div style="font-weight:700;color:#58a6ff;margin-bottom:6px">📝 計算步驟</div>';
          html += '① 列出算式<br>② 逐步計算<br>③ 約分成最簡分數';
          html += '</div>';
        }
      } else if (family === 'percent'){
        var pVal = 0;
        var m = text.match(/(\d+)\s*[%％折]/);
        if (m) pVal = parseInt(m[1], 10);
        if (/折/.test(text)) pVal = pVal * 10;
        if (pVal > 0 && pVal <= 100){
          html += buildPercentGridSVG(pVal);
          /* Step-by-step narration */
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '① 100 格方格紙，塗滿 <strong>' + pVal + '</strong> 格<br>';
          html += '② 塗色佔全部的 <strong>' + pVal + '%</strong>';
          if (/折/.test(text)){
            var foldVal = text.match(/(\d+)\s*折/);
            if (foldVal) html += ' = <strong>' + foldVal[1] + ' 折</strong>';
          }
          html += '</div>';
          /* If an original amount is in the text, show comparison bar */
          var origMatch = text.match(/(?:原[價價]|定價|售價|全[部體])\s*(\d+)/);
          if (origMatch){
            var origAmt = parseInt(origMatch[1],10);
            var discAmt = Math.round(origAmt * pVal / 100);
            html += buildComparisonBarSVG([
              { label: '原價', value: origAmt },
              { label: pVal+'%', value: discAmt }
            ]);
            html += '<div style="font-size:11px;color:#e5e7eb;margin:2px 0">③ 原價 <strong>' + origAmt + '</strong> → ' + pVal + '% = <strong>' + discAmt + '</strong></div>';
          }
        }
      } else if (family === 'decimal'){
        var decs = [];
        var dm = text.match(/\d+\.\d+/g);
        if (dm) for (var di = 0; di < dm.length; di++) decs.push(parseFloat(dm[di]));
        if (decs.length > 0){
          html += buildNumberLineSVG(decs);
          /* Place value decomposition for the first decimal */
          html += '<div style="font-size:10px;color:#9ca3af;margin:2px 0 0 0">▼ 位值分解：</div>';
          html += buildPlaceValueSVG(decs[0]);
          /* Step-by-step narration */
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '① 在數線上標出 <strong>' + decs.join(', ') + '</strong><br>';
          html += '② 看每個小數的位值分解<br>';
          if (decs.length >= 2) html += '③ 比較大小或準備運算';
          html += '</div>';
        }
      } else if (family === 'volume' && ints.length >= 2){
        /* 3D isometric box for volume questions */
        /* Check for composite volume (multiple boxes A, B, C) */
        var compositeMatch = text.match(/[A-C][\s：:]+長\s*(\d+)\s*(?:公分|cm)?\s*[、,]\s*寬\s*(\d+)\s*(?:公分|cm)?\s*[、,]\s*高\s*(\d+)/g);
        if (compositeMatch && compositeMatch.length >= 2){
          /* Composite: draw each box with label */
          var unitM = text.match(/公分|cm|公尺|m/);
          var vUnit = unitM ? unitM[0] : '';
          var boxLabels = ['A','B','C','D','E'];
          var svgParts = [];
          var totalFormula = [];
          var totalVol = 0;
          for (var ci = 0; ci < compositeMatch.length; ci++){
            var cm = compositeMatch[ci].match(/([A-C])[\s：:]+長\s*(\d+)\s*(?:公分|cm)?\s*[、,]\s*寬\s*(\d+)\s*(?:公分|cm)?\s*[、,]\s*高\s*(\d+)/);
            if (cm){
              var cl = parseInt(cm[2],10), cw = parseInt(cm[3],10), ch = parseInt(cm[4],10);
              var cLabel = cm[1] || boxLabels[ci];
              svgParts.push(buildIsometricBoxSVG(cl, cw, ch, { unit: vUnit, label: cLabel + '：' + cl + '×' + cw + '×' + ch }));
              totalFormula.push('(' + cl + '×' + cw + '×' + ch + ')');
              totalVol += cl * cw * ch;
            }
          }
          html += '<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">' + svgParts.join('') + '</div>';
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '① 分解成 ' + compositeMatch.length + ' 個長方體<br>';
          html += '② V = ' + totalFormula.join(' + ') + '<br>';
          html += '③ 各自算出體積再相加 = <strong>' + totalVol + '</strong>' + (vUnit ? ' ' + vUnit : '');
          html += '</div>';
        } else {
          /* Smart dimension extraction (handles rect_find_height etc.) */
          var vd = parseVolumeDims(text, q.kind);
          var vl = vd.l || 1, vw = vd.w || 1, vh = vd.h || 0;
          var vUnit = vd.unit;
          var vUnk = vd.unknownDim;
        if (vh > 0){
          var boxLabel2 = vUnk === 'h' ? '高 = 體積 ÷ (長×寬)' : '體積 = 長×寬×高';
          html += buildIsometricBoxSVG(vl, vw, vh, { unit: vUnit, label: boxLabel2, unknownDim: vUnk });
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          if (vUnk === 'h'){
            html += '① 已知：長 = <strong>' + vd.l + '</strong>、寬 = <strong>' + vd.w + '</strong>、體積 = <strong>' + vd.vol + '</strong><br>';
            html += '② 底面積 = 長 × 寬 = <strong>' + vd.l + ' × ' + vd.w + '</strong><br>';
            html += '③ 高 = 體積 ÷ 底面積';
          } else {
            html += '① 底面排好：<strong>' + vl + ' × ' + vw + '</strong>' + (vUnit ? ' ' + vUnit : '') + '<br>';
            html += '② 一層一層往上疊 <strong>' + vh + '</strong> 層<br>';
            html += '③ 體積 = 底面積 × 高';
          }
          html += '</div>';
        } else {
          html += buildIsometricBoxSVG(vl, vw, 1, { unit: vUnit, label: '面積 = 長×寬' });
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '① 長 = <strong>' + vl + '</strong>　寬 = <strong>' + vw + '</strong><br>';
          html += '② 面積 = 長 × 寬';
          html += '</div>';
        }
        }
      } else if (family === 'time'){
        /* Clock face for time questions */
        var timeRe = /(\d{1,2})\s*[:：時]\s*(\d{1,2})?/g;
        var times = [];
        var tm;
        while ((tm = timeRe.exec(text)) !== null){
          times.push({ h: parseInt(tm[1],10), m: parseInt(tm[2]||'0',10) });
        }
        if (times.length >= 2){
          /* Show start and end clocks with span arc */
          html += '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px">';
          html += buildClockFaceSVG(times[0].h, times[0].m, {
            label: '起 '+times[0].h+':'+('0'+times[0].m).slice(-2),
            h2: times[1].h, m2: times[1].m, size: 110
          });
          html += buildClockFaceSVG(times[1].h, times[1].m, {
            label: '迄 '+times[1].h+':'+('0'+times[1].m).slice(-2),
            size: 110
          });
          html += '</div>';
        } else if (times.length === 1){
          html += buildClockFaceSVG(times[0].h, times[0].m, {
            label: times[0].h+':'+('0'+times[0].m).slice(-2),
            size: 110
          });
        }
      }

      /* Average: leveling bar chart */
      if (family === 'average' && ints.length >= 2){
        html += buildLevelingSVG(ints.slice(0, Math.min(ints.length, 8)));
      }

      /* Generic: number bond if there are distinct numbers */
      if (family === 'generic' && ints.length >= 2){
        var bondWhole = ints[0];
        var bondParts = ints.slice(1, Math.min(ints.length, 6));
        html += buildNumberBondSVG(bondParts, bondWhole);
      }

      if (needsBaseSwitchWarning(text)){
        html += '<div class="he-base-switch">⚠️ 注意：圖中第二段的顏色是從「剩下」的部分切出來的！</div>';
      }
      return html;
    }

    /* --- L3: 讀圖得分數 (grid + labels) --- */
    if (lv === 3){
      html += '<div class="he-rich-l3">' + highlightKeywords(escapeHTML(tpl.L3).replace(/\n/g, '<br>')) + '</div>';

      if ((family === 'fracRemain' || family === 'fracWord') && fracs.length >= 1){
        /* Build a grid showing the fraction decomposition */
        if (fracs.length >= 2){
          var f1 = fracs[0], f2 = fracs[1];
          var totalCells = lcm(f1.den, f2.den) || f1.den * f2.den;
          var cells1 = totalCells * f1.num / f1.den;
          var remaining = totalCells - cells1;
          var cells2 = remaining * f2.num / f2.den;
          var cellsLeft = totalCells - cells1 - cells2;

          /* Pick grid dimensions close to square */
          var gridCols = Math.min(totalCells, 10);
          var gridRows = Math.ceil(totalCells / gridCols);
          var cm = [
            { count: Math.round(cells1), color: '#ef4444', label: '🟥 '+f1.num+'/'+f1.den+' = '+Math.round(cells1)+'/'+totalCells },
            { count: Math.round(cells2), color: '#f97316', label: '🟧 '+Math.round(cells2)+'/'+totalCells },
            { count: Math.round(cellsLeft), color: '#3b82f6', label: '🟦 剩 '+Math.round(cellsLeft)+'/'+totalCells }
          ];
          html += buildGridSVG(gridRows, gridCols, cm);
          /* Detailed narration matching reference example */
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '整個長方形 = ' + f1.den + ' × ' + f2.den + ' = <strong>' + totalCells + '</strong> 小格<br>';
          html += '每個小格 = 1/' + totalCells + '<br><br>';
          html += '🟥 第1次用掉 = <strong>' + Math.round(cells1) + '</strong> 格 = ' + Math.round(cells1) + '/' + totalCells + ' = ' + f1.num + '/' + f1.den + '<br>';
          html += '🟧 第2次用掉 = <strong>' + Math.round(cells2) + '</strong> 格 = ' + Math.round(cells2) + '/' + totalCells + '<br>';
          html += '🟦 剩下 = <strong>' + Math.round(cellsLeft) + '</strong> 格 = ' + Math.round(cellsLeft) + '/' + totalCells + '<br><br>';
          html += '💡 驗算：' + Math.round(cells1) + ' + ' + Math.round(cells2) + ' + ' + Math.round(cellsLeft) + ' = ' + totalCells + ' ✓';
          html += '</div>';
          /* Tree breakdown: whole → parts */
          html += '<div style="font-size:10px;color:#9ca3af;margin:4px 0 0 0">▼ 分拆結構：</div>';
          html += buildTreeDiagramSVG(
            { label: '全部', value: '1' },
            [
              { label: '🟥 '+f1.num+'/'+f1.den, color: '#ef4444' },
              { label: '🟧 '+Math.round(cells2)+'/'+totalCells, color: '#f97316' },
              { label: '🟦 '+Math.round(cellsLeft)+'/'+totalCells, color: '#3b82f6' }
            ]
          );
        } else if (fracs.length === 1){
          var f = fracs[0];
          var gc = Math.min(f.den, 10);
          var gr = Math.ceil(f.den / gc);
          html += buildGridSVG(gr, gc, [
            { count: f.num, color: '#ef4444', label: f.num+'/'+f.den },
            { count: f.den - f.num, color: '#374151', label: '剩 '+(f.den-f.num)+'/'+f.den }
          ]);
          /* Narration for fracWord with single fraction */
          if (family === 'fracWord' && ints.length >= 1){
            html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
            html += '📊 全部 = <strong>' + ints[0] + '</strong><br>';
            html += '取其中 <strong>' + f.num + '/' + f.den + '</strong> → ' + ints[0] + ' × ' + f.num + '/' + f.den + ' = ？（自行算）<br>';
            html += '💡 格子裡塗色的 <strong>' + f.num + '</strong> 格（共 ' + f.den + ' 格）就是答案的比例';
            html += '</div>';
          }
        }
      } else if (family === 'fracAdd' && fracs.length >= 1){
        /* Grid for fraction addition: show each fraction in common denominator */
        if (fracs.length >= 2){
          var fa1 = fracs[0], fa2 = fracs[1];
          var comD3 = lcm(fa1.den, fa2.den) || fa1.den * fa2.den;
          if (comD3 > 0 && comD3 <= 60){
            var eq1 = fa1.num * (comD3 / fa1.den);
            var eq2 = fa2.num * (comD3 / fa2.den);
            var total3 = eq1 + eq2;
            var gc3 = Math.min(comD3, 10);
            var gr3 = Math.ceil(comD3 / gc3);
            var addColors = ['#ef4444','#3b82f6'];
            var cm3 = [
              { count: Math.round(eq1), color: addColors[0], label: '🟥 '+fa1.num+'/'+fa1.den+' = '+Math.round(eq1)+'/'+comD3 },
              { count: Math.round(eq2), color: addColors[1], label: '🟦 '+fa2.num+'/'+fa2.den+' = '+Math.round(eq2)+'/'+comD3 },
              { count: Math.max(0, comD3 - Math.round(eq1) - Math.round(eq2)), color: '#374151', label: '空' }
            ];
            html += buildGridSVG(gr3, gc3, cm3);
            /* Detailed narration for fracAdd L3 */
            var isAddL3 = !/減|差|少|扣/.test(text);
            html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
            html += '通分後分母 = <strong>' + comD3 + '</strong><br><br>';
            html += '🟥 ' + fa1.num + '/' + fa1.den + ' = <strong>' + Math.round(eq1) + '/' + comD3 + '</strong> → ' + Math.round(eq1) + ' 格<br>';
            html += '🟦 ' + fa2.num + '/' + fa2.den + ' = <strong>' + Math.round(eq2) + '/' + comD3 + '</strong> → ' + Math.round(eq2) + ' 格<br><br>';
            html += '📊 ' + (isAddL3 ? '加' : '減') + '起來 = ' + Math.round(eq1) + ' ' + (isAddL3 ? '+' : '−') + ' ' + Math.round(eq2) + ' = <strong>' + Math.round(total3) + '</strong> 格<br>';
            html += '→ <strong>' + Math.round(total3) + '/' + comD3 + '</strong>';
            /* Check if reducible */
            var gcdL3 = gcd(Math.round(total3), comD3);
            if (gcdL3 > 1){
              html += ' → 約分 = <strong>' + (Math.round(total3)/gcdL3) + '/' + (comD3/gcdL3) + '</strong>';
            }
            html += '</div>';
          }
        } else {
          var fa = fracs[0];
          var gc4 = Math.min(fa.den, 10);
          var gr4 = Math.ceil(fa.den / gc4);
          html += buildGridSVG(gr4, gc4, [
            { count: fa.num, color: '#ef4444', label: fa.num+'/'+fa.den },
            { count: fa.den - fa.num, color: '#374151', label: '' }
          ]);
        }
      } else if (family === 'percent'){
        var pVal2 = 0;
        var m2 = text.match(/(\d+)\s*[%％折]/);
        if (m2) pVal2 = parseInt(m2[1], 10);
        if (/折/.test(text)) pVal2 = pVal2 * 10;
        if (pVal2 > 0){
          html += buildPercentGridSVG(pVal2);
          html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0;line-height:1.6">';
          html += '📊 <strong>' + pVal2 + '</strong> 格塗色 / 100 格 = <strong>' + pVal2 + '%</strong><br>';
          /* Show original quantity if found */
          var origL3 = 0;
          for (var oq3 = 0; oq3 < ints.length; oq3++){
            if (m2 && ints[oq3] !== parseInt(m2[1],10)){ origL3 = ints[oq3]; break; }
          }
          if (origL3 > 0){
            html += '原量 = <strong>' + origL3 + '</strong> → ' + origL3 + ' × ' + pVal2 + '/100 = ？（自行算）';
          }
          html += '</div>';
        }
      } else if (family === 'decimal'){
        /* Place-value decomposition for L3 */
        var decs3 = [];
        var dm3 = text.match(/\d+\.\d+/g);
        if (dm3) for (var di3 = 0; di3 < dm3.length; di3++) decs3.push(parseFloat(dm3[di3]));
        if (decs3.length > 0){
          html += '<div style="font-size:12px;color:#d29922;margin:4px 0">';
          html += '📊 分解每一位的值：</div>';
          html += buildPlaceValueSVG(decs3[0]);
          /* Show decomposition text */
          var decStr = String(decs3[0]);
          var dParts = decStr.split('.');
          var intD = dParts[0] || '0';
          var fracD = dParts[1] || '';
          var decomp = [];
          if (parseInt(intD,10) > 0) decomp.push(intD + ' 個');
          var dNames3 = ['十分位','百分位','千分位'];
          for (var dp = 0; dp < fracD.length && dp < 3; dp++){
            var dg = parseInt(fracD[dp],10);
            if (dg > 0) decomp.push(dg + ' 個 ' + dNames3[dp]);
          }
          if (decomp.length > 0){
            html += '<div style="font-size:11px;color:#9ca3af;margin:2px 0">'+decs3[0]+' = '+decomp.join(' + ')+'</div>';
          }
          /* If 2+ decimals, also show second decomposition + comparison hint */
          if (decs3.length >= 2){
            html += buildPlaceValueSVG(decs3[1]);
            var decStr2 = String(decs3[1]);
            var dParts2 = decStr2.split('.');
            var intD2 = dParts2[0] || '0';
            var fracD2 = dParts2[1] || '';
            var decomp2 = [];
            if (parseInt(intD2,10) > 0) decomp2.push(intD2 + ' 個');
            for (var dp2 = 0; dp2 < fracD2.length && dp2 < 3; dp2++){
              var dg2 = parseInt(fracD2[dp2],10);
              if (dg2 > 0) decomp2.push(dg2 + ' 個 ' + dNames3[dp2]);
            }
            if (decomp2.length > 0){
              html += '<div style="font-size:11px;color:#9ca3af;margin:2px 0">'+decs3[1]+' = '+decomp2.join(' + ')+'</div>';
            }
            html += '<div style="font-size:11px;color:#e5e7eb;margin:4px 0">💡 兩個小數一起比較：逐位對齊，從最左開始比</div>';
          }
        }
      } else if (family === 'time'){
        /* Read clock: count hours + minutes from the arc */
        var timeRe3 = /(\d{1,2})\s*[:：時]\s*(\d{1,2})?/g;
        var times3 = [];
        var tm3;
        while ((tm3 = timeRe3.exec(text)) !== null){
          times3.push({ h: parseInt(tm3[1],10), m: parseInt(tm3[2]||'0',10) });
        }
        if (times3.length >= 2){
          var diffMin = (times3[1].h * 60 + times3[1].m) - (times3[0].h * 60 + times3[0].m);
          if (diffMin < 0) diffMin += 24 * 60;
          var dH = Math.floor(diffMin / 60);
          var dM = diffMin % 60;
          html += '<div style="font-size:12px;color:#d29922;margin:4px 0">';
          html += '📊 從鐘面讀出：走了 <strong>' + dH + '</strong> 大格（小時）';
          if (dM > 0) html += ' + <strong>' + dM + '</strong> 小格（分鐘）';
          html += ' = <strong>' + dH + ' 時 ' + dM + ' 分</strong>';
          html += '</div>';
        }
      } else if (family === 'volume' && ints.length >= 2){
        /* Read the box: count layers x per-layer units */
        var vd3 = parseVolumeDims(text, q.kind);
        html += '<div style="font-size:12px;color:#d29922;margin:4px 0">';
        if (vd3.unknownDim === 'h'){
          html += '📊 底面積 = ' + vd3.l + ' × ' + vd3.w + ' = <strong>' + (vd3.l * vd3.w) + '</strong><br>';
          html += '高 = 體積 ÷ 底面積 = ' + vd3.vol + ' ÷ ' + (vd3.l * vd3.w) + ' = ？（自行算）';
        } else {
          var v3l = vd3.l || ints[0], v3w = vd3.w || ints[1], v3h = vd3.h || (ints.length > 2 ? ints[2] : 1);
          html += '📊 底面 = ' + v3l + ' × ' + v3w + ' = <strong>' + (v3l * v3w) + '</strong> 個';
          if (v3h > 1){
            html += '　疊 <strong>' + v3h + '</strong> 層 → 合計 <strong>' + (v3l * v3w) + ' × ' + v3h + '</strong> = ？（自行算）';
          }
        }
        html += '</div>';
      } else if (family === 'average' && ints.length >= 2){
        /* Show the leveling interpretation */
        var sum3 = ints.reduce(function(s,v){ return s+v; }, 0);
        html += '<div style="font-size:12px;color:#d29922;margin:4px 0">';
        html += '📊 削補後每份一樣高：<br>';
        html += '合計 = ' + ints.join(' + ') + ' = <strong>' + sum3 + '</strong><br>';
        html += '共 <strong>' + ints.length + '</strong> 份 → 平均 = '+sum3+' ÷ '+ints.length+' = ？（自行算）';
        html += '</div>';
        /* Bar chart for data visualization */
        var barItems = [];
        for (var bi = 0; bi < ints.length && bi < 8; bi++){
          barItems.push({ label: '#' + (bi + 1), value: ints[bi] });
        }
        html += buildBarChartSVG(barItems);
        html += buildLevelingSVG(ints.slice(0, Math.min(ints.length, 8)));
      }

      return html;
    }

    /* --- L4: 算式收斂 + 合理性檢查 --- */
    if (lv === 4){
      html += '<div class="he-rich-l4">' + highlightKeywords(escapeHTML(tpl.L4).replace(/\n/g, '<br>')) + '</div>';

      /* Family-specific formula scaffolding */
      if (family === 'fracRemain' && fracs.length >= 2){
        var f1r = fracs[0], f2r = fracs[1];
        var remainNum = f1r.den - f1r.num;
        html += '<div class="he-formula">';
        if (ints.length >= 1 && ints[0] > 0){
          /* Context-specific with actual numbers (but still □ for final answer) */
          var total4r = ints[0];
          var step1Val = total4r * remainNum / f1r.den;
          var step1Show = Number.isInteger(step1Val) ? String(step1Val) : (total4r + '×' + remainNum + '/' + f1r.den);
          html += '<div class="he-step-row">步驟① 第1次剩 = ' + total4r + ' × ' + remainNum + '/' + f1r.den + ' = <strong>' + step1Show + '</strong></div>';
          html += '<div class="he-step-row">步驟② 第2次用 = ' + step1Show + ' × ' + f2r.num + '/' + f2r.den + ' = <span class="he-placeholder">□</span></div>';
          html += '<div class="he-step-row">步驟③ 最後剩 = ' + step1Show + ' − <span class="he-placeholder">□</span> = <span class="he-placeholder">□</span></div>';
        } else {
          /* Pure fraction form */
          html += '<div class="he-step-row">步驟① 1 − ' + f1r.num + '/' + f1r.den + ' = ' + remainNum + '/' + f1r.den + '（剩下）</div>';
          html += '<div class="he-step-row">步驟② ' + remainNum + '/' + f1r.den + ' × ' + f2r.num + '/' + f2r.den + ' = <span class="he-placeholder">□</span>（第二段量）</div>';
          html += '<div class="he-step-row">步驟③ 剩下 − 第二段 = <span class="he-placeholder">□</span>（最終答案）</div>';
        }
        html += '</div>';
        html += '<div class="he-check-ok">✅ 第二段 &lt; 剩下？全部 &gt; 答案？</div>';
        html += '<div class="he-check-ok">✅ 剩下 ≥ 0 → 合理</div>';
        html += '<div class="he-check-bad">❌ 常見錯誤：1 − ' + f1r.num + '/' + f1r.den + ' − ' + f2r.num + '/' + f2r.den + ' ← 錯！<br>　　第二次的 ' + f2r.num + '/' + f2r.den + ' 不是從全部算的！</div>';
      } else if (family === 'fracWord' && fracs.length >= 1){
        var fw = fracs[0];
        html += '<div class="he-formula">';
        if (ints.length >= 1 && ints[0] > 0){
          var fwTotal = ints[0];
          var fwProd = fwTotal * fw.num;
          html += '<div class="he-step-row">步驟① 列式：' + fwTotal + ' × ' + fw.num + '/' + fw.den + '</div>';
          html += '<div class="he-step-row">步驟② 先算分子：' + fwTotal + ' × ' + fw.num + ' = <strong>' + fwProd + '</strong></div>';
          html += '<div class="he-step-row">步驟③ 再除以分母：<strong>' + fwProd + '</strong> ÷ ' + fw.den + ' = <span class="he-placeholder">□</span></div>';
        } else {
          html += '<div class="he-step-row">步驟① 列式：全部 × ' + fw.num + '/' + fw.den + '</div>';
          html += '<div class="he-step-row">步驟② 先算分子乘積 = <span class="he-placeholder">□</span></div>';
          html += '<div class="he-step-row">步驟③ 再除以分母 = <span class="he-placeholder">□</span></div>';
        }
        html += '</div>';
        html += '<div class="he-check-ok">✅ 結果 &lt; 全部？分數 &lt; 1 → 結果 &lt; 全部</div>';
        html += '<div class="he-check-bad">❌ 常見錯：乘完忘記除以分母、或把分子分母搞反</div>';
      } else if (family === 'fracAdd' && fracs.length >= 2){
        var fa4a = fracs[0], fa4b = fracs[1];
        var cd4 = lcm(fa4a.den, fa4b.den) || fa4a.den * fa4b.den;
        var eq4a = fa4a.num * (cd4 / fa4a.den);
        var eq4b = fa4b.num * (cd4 / fa4b.den);
        var isAdd = !/減|差|少|扣/.test(text);
        html += '<div class="he-formula">';
        html += '<div class="he-step-row">步驟① 通分：分母 = <strong>' + cd4 + '</strong></div>';
        html += '<div class="he-step-row">' + escapeHTML(fa4a.num + '/' + fa4a.den) + ' = <strong>' + eq4a + '/' + cd4 + '</strong></div>';
        html += '<div class="he-step-row">' + escapeHTML(fa4b.num + '/' + fa4b.den) + ' = <strong>' + eq4b + '/' + cd4 + '</strong></div>';
        html += '<div class="he-step-row">步驟② 分子 ' + (isAdd ? '加' : '減') + '：' + eq4a + ' ' + (isAdd ? '+' : '−') + ' ' + eq4b + ' = <span class="he-placeholder">□</span></div>';
        html += '<div class="he-step-row">步驟③ 約分到最簡 → <span class="he-placeholder">□</span>/<span class="he-placeholder">□</span></div>';
        html += '</div>';
        html += '<div class="he-check-ok">✅ ' + (isAdd ? '加的結果 ≥ 兩個分數中較大的' : '減的結果 ≤ 被減數') + '</div>';
      } else if (family === 'percent'){
        var m3 = text.match(/(\d+)\s*[%％]/); var m3f = text.match(/(\d+)\s*折/);
        /* Try to extract original quantity */
        var origQty = 0;
        if (ints.length > 0){
          for (var oq = 0; oq < ints.length; oq++){
            if (m3 && ints[oq] !== parseInt(m3[1],10)){ origQty = ints[oq]; break; }
            if (m3f && ints[oq] !== parseInt(m3f[1],10)){ origQty = ints[oq]; break; }
          }
        }
        html += '<div class="he-formula">';
        if (m3){
          var pct4 = parseInt(m3[1],10);
          html += '<div class="he-step-row">步驟① 寫出倍率：<strong>'+pct4+'%</strong> = <strong>'+pct4+'/100</strong></div>';
          if (origQty > 0){
            html += '<div class="he-step-row">步驟② 列式：'+origQty+' × '+pct4+'/100 = <span class="he-placeholder">□</span></div>';
          } else {
            html += '<div class="he-step-row">步驟② 列式：原量 × '+pct4+'/100 = <span class="he-placeholder">□</span></div>';
          }
          html += '<div class="he-step-row">步驟③ 合理性檢查</div>';
        } else if (m3f){
          var disc4 = parseInt(m3f[1],10);
          html += '<div class="he-step-row">步驟① 寫出倍率：<strong>'+disc4+'折</strong> = <strong>'+disc4+'/10 = 0.'+disc4+'</strong></div>';
          if (origQty > 0){
            html += '<div class="he-step-row">步驟② 列式：'+origQty+' × 0.'+disc4+' = <span class="he-placeholder">□</span></div>';
          } else {
            html += '<div class="he-step-row">步驟② 列式：原價 × 0.'+disc4+' = <span class="he-placeholder">□</span></div>';
          }
          html += '<div class="he-step-row">步驟③ 合理性檢查</div>';
        } else {
          html += '<div class="he-step-row">步驟① 找出百分率或折扣率</div>';
          html += '<div class="he-step-row">步驟② 列式：原量 × 倍率 = <span class="he-placeholder">□</span></div>';
        }
        html += '</div>';
        html += '<div class="he-check-ok">✅ 打折 → 結果 &lt; 原價；加成 → 結果 &gt; 原量</div>';
        html += '<div class="he-check-bad">❌ 常見錯：%忘記÷100、折數搞反</div>';
      } else if (family === 'decimal'){
        /* Detect decimal values and operation from question text */
        var decs4 = [];
        var dm4 = text.match(/\d+\.\d+/g);
        if (dm4) for (var di4 = 0; di4 < dm4.length; di4++) decs4.push(parseFloat(dm4[di4]));
        var decPlaces4 = 0;
        if (dm4) for (var dp4 = 0; dp4 < dm4.length; dp4++){
          var dotPart = dm4[dp4].split('.')[1] || '';
          decPlaces4 += dotPart.length;
        }
        html += '<div class="he-formula">';
        html += '<div class="he-step-row">步驟① 先當整數算（去掉小數點）</div>';
        if (decs4.length >= 2){
          /* Show actual integer conversions */
          var intForm0 = Math.round(decs4[0] * Math.pow(10, (dm4[0].split('.')[1]||'').length));
          var intForm1 = Math.round(decs4[1] * Math.pow(10, (dm4[1].split('.')[1]||'').length));
          html += '<div class="he-step-row">' + escapeHTML(String(decs4[0])) + ' → <strong>' + intForm0 + '</strong>　' + escapeHTML(String(decs4[1])) + ' → <strong>' + intForm1 + '</strong></div>';
        } else if (decs4.length === 1){
          var intForm = Math.round(decs4[0] * Math.pow(10, (dm4[0].split('.')[1]||'').length));
          html += '<div class="he-step-row">' + escapeHTML(String(decs4[0])) + ' → <strong>' + intForm + '</strong></div>';
        }
        html += '<div class="he-step-row">步驟② 整數運算：<span class="he-placeholder">□</span></div>';
        html += '<div class="he-step-row">步驟③ 放回小數點（' + (decPlaces4 > 0 ? '共 <strong>' + decPlaces4 + '</strong> 位' : '位數加總') + '）→ <span class="he-placeholder">□</span></div>';
        html += '</div>';
        html += '<div class="he-check-ok">✅ 用整數近似值檢查量級是否合理</div>';
        html += '<div class="he-check-bad">❌ 常見錯：小數點位數數錯（乘法相加、除法相減）</div>';
      } else if (family === 'time'){
        var timeRe4 = /(\d{1,2})\s*[:：時]\s*(\d{1,2})?/g;
        var times4 = [];
        var tm4;
        while ((tm4 = timeRe4.exec(text)) !== null){
          times4.push({ h: parseInt(tm4[1],10), m: parseInt(tm4[2]||'0',10) });
        }
        if (times4.length >= 2){
          var needBorrow4 = times4[1].m < times4[0].m;
          html += '<div class="he-formula">';
          html += '<div class="he-step-row">步驟① 列式：<strong>'+times4[1].h+'</strong>時<strong>'+('0'+times4[1].m).slice(-2)+'</strong>分 − <strong>'+times4[0].h+'</strong>時<strong>'+('0'+times4[0].m).slice(-2)+'</strong>分</div>';
          if (needBorrow4){
            var borrowedM = times4[1].m + 60;
            var borrowedH = times4[1].h - 1;
            html += '<div class="he-step-row">步驟② 分鐘不夠減 → 借 1 小時 = 60 分 → <strong>' + borrowedH + '</strong>時<strong>' + borrowedM + '</strong>分</div>';
          }
          html += '<div class="he-step-row">步驟'+(needBorrow4?'③':'②')+' 計算：<span class="he-placeholder">□</span> 時 <span class="he-placeholder">□</span> 分</div>';
          html += '</div>';
          html += '<div class="he-check-ok">✅ 結果轉回鐘面看是否合理</div>';
          html += '<div class="he-check-bad">❌ 常見錯：忘記借位（60進位）</div>';
        }
      } else if (family === 'volume' && ints.length >= 2){
        var vd4 = parseVolumeDims(text, q.kind);
        html += '<div class="he-formula">';
        if (vd4.unknownDim === 'h'){
          var ba4h = vd4.l * vd4.w;
          html += '<div class="he-step-row">步驟① 底面積 = ' + vd4.l + ' × ' + vd4.w + ' = <strong>' + ba4h + '</strong></div>';
          html += '<div class="he-step-row">步驟② 高 = 體積 ÷ 底面積 = ' + vd4.vol + ' ÷ ' + ba4h + ' = <span class="he-placeholder">□</span></div>';
          html += '<div class="he-step-row">步驟③ 寫上單位（公分 or 公尺）</div>';
        } else if (vd4.h > 0){
          var baseArea4 = vd4.l * vd4.w;
          html += '<div class="he-step-row">步驟① 底面積 = ' + vd4.l + ' × ' + vd4.w + ' = <strong>' + baseArea4 + '</strong></div>';
          html += '<div class="he-step-row">步驟② 體積 = <strong>' + baseArea4 + '</strong> × ' + vd4.h + ' = <span class="he-placeholder">□</span></div>';
          html += '<div class="he-step-row">步驟③ 寫上單位（立方公分 or 立方公尺）</div>';
        } else {
          html += '<div class="he-step-row">步驟① 面積 = ' + vd4.l + ' × ' + vd4.w + ' = <span class="he-placeholder">□</span></div>';
          html += '<div class="he-step-row">步驟② 寫上單位（平方公分 or 平方公尺）</div>';
        }
        html += '</div>';
        html += '<div class="he-check-ok">✅ 組合體：先拆成基本形再加減</div>';
        html += '<div class="he-check-bad">❌ 常見錯：搞混面積（²）與體積（³）單位</div>';
      } else if (family === 'average' && ints.length >= 2){
        var sum4 = ints.reduce(function(s,v){ return s+v; }, 0);
        html += '<div class="he-formula">';
        html += '<div class="he-step-row">步驟① 加總：' + ints.join(' + ') + ' = <strong>' + sum4 + '</strong></div>';
        html += '<div class="he-step-row">步驟② 除以個數：<strong>' + sum4 + '</strong> ÷ ' + ints.length + ' = <span class="he-placeholder">□</span></div>';
        html += '</div>';
        html += '<div class="he-check-ok">✅ 答案介於 ' + Math.min.apply(null, ints) + ' 和 ' + Math.max.apply(null, ints) + ' 之間？</div>';
        html += '<div class="he-check-bad">❌ 常見錯：忘記除以個數、或把「多出的量」當平均</div>';
      }

      html += '<div class="he-finish">🏁 填入你的答案</div>';
      return html;
    }

    return html;
  }

  function escapeHTML(s){
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  /* ============================================================
   * 2. 基準量切換提醒
   * ============================================================ */
  var BASE_SWITCH_KEYWORDS = /剩下的|剩餘的|餘下的|再[取看用拿]|又[取看用拿]|第二次/;

  function needsBaseSwitchWarning(questionText){
    return BASE_SWITCH_KEYWORDS.test(String(questionText || ''));
  }

  function getBaseSwitchReminder(questionText){
    if (!needsBaseSwitchWarning(questionText)) return '';
    return '⚠️ 注意基準切換：第二次操作不是對「全部」，而是對「前一步剩下的量」。\n　請先算出第一步結果，再用它當第二步的基準。';
  }

  /* ============================================================
   * 3. Level 3 嚴格防洩漏
   * ============================================================ */
  function normalizeForCompare(s){
    return String(s || '').replace(/\s+/g, '').replace(/,/g, '');
  }

  function stripAnswerFromHint(hintText, answer){
    var h = String(hintText || '');
    var ans = normalizeForCompare(answer);
    if (!ans || ans.length < 1) return h;

    /* Build set of answer variants to strip */
    var variants = [String(answer || '').trim()];

    /* If answer is fraction, also strip decimal equivalent */
    var fMatch = String(answer || '').match(/^(\d+)\s*[\/／]\s*(\d+)$/);
    if (fMatch){
      var decVal = parseInt(fMatch[1],10) / parseInt(fMatch[2],10);
      if (isFinite(decVal)){
        var decStr = String(Math.round(decVal * 10000) / 10000);
        variants.push(decStr);
        /* Also add reduced form */
        var g = gcd(parseInt(fMatch[1],10), parseInt(fMatch[2],10));
        if (g > 1) variants.push((parseInt(fMatch[1],10)/g) + '/' + (parseInt(fMatch[2],10)/g));
      }
    }
    /* If answer is decimal, also strip equivalent fraction */
    var dMatch = String(answer || '').match(/^(\d+)\.(\d+)$/);
    if (dMatch){
      var places = dMatch[2].length;
      var den = Math.pow(10, places);
      var num = parseInt(dMatch[1] + dMatch[2], 10);
      var g2 = gcd(num, den);
      variants.push((num/g2) + '/' + (den/g2));
    }

    /* If answer has units, also strip the bare number */
    var unitMatch = String(answer || '').match(/^([\d.\/]+)\s*([^\d.\/]+)$/);
    if (unitMatch){
      variants.push(unitMatch[1].trim());
    }

    /* Replace all variants */
    for (var vi = 0; vi < variants.length; vi++){
      var v = variants[vi];
      if (!v || v.length < 1) continue;
      var hNorm = normalizeForCompare(h);
      var vNorm = normalizeForCompare(v);
      if (vNorm && hNorm.indexOf(vNorm) !== -1){
        h = h.replace(new RegExp(escapeRegex(v), 'g'), '（先自己算）');
      }
    }

    /* Catch patterns like "答案是 X", "結果是 X", "答: X", "= X (最終)" */
    h = h.replace(/(?:答案[是為]?|結果[是為]?|最後[是為]?|答\s*[:：]|所以|因此|得到|等於)\s*[:：]?\s*\d[\d.\/\s]*(?:\s*[a-zA-Z%㎡³元個頁公分公尺]*)?\s*[。.！!]?/g, '（請自行完成最後計算）');
    h = h.replace(/=\s*\d[\d.\/\s]*\s*$/gm, '= ？（自行計算）');
    /* "算出 X" or "得 X" at end of sentence */
    h = h.replace(/(?:算出|得出|算得)\s*\d[\d.\/\s]*\s*$/gm, '？（自行計算）');

    return h;
  }

  function escapeRegex(s){
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * enforceL3Gate(hintText, question)
   * L3 hard gate: strips final answer, ensures only intermediate values remain.
   */
  function enforceL3Gate(hintText, q){
    if (!q) return hintText;
    var h = stripAnswerFromHint(hintText, q.answer);
    /* Extra safety: if the answer appears anywhere in normalized form, blank it */
    var ansNorm = normalizeForCompare(q.answer);
    var hNorm = normalizeForCompare(h);
    if (ansNorm && ansNorm.length >= 1 && hNorm.indexOf(ansNorm) !== -1){
      h = h + '\n⛔ 不直接給最後數值，請自行完成計算。';
    }
    return h;
  }

  /* ============================================================
   * 4. 錯因對應提示 — 常見錯誤 → 補救句
   * ============================================================ */
  var MISCONCEPTION_MAP = {
    /* 分數 */
    'base_switch_error': {
      detect: function(q, wrongAns){
        /* Student treated "剩下的 1/3" as "全部的 1/3" */
        if (!needsBaseSwitchWarning(q.question)) return false;
        var total = extractFirstNumber(q.question);
        if (!total) return false;
        /* Check if wrong answer matches "total × second_fraction" (wrong base) */
        return false; /* Conservative: use tag-based matching below */
      },
      remedy: '你可能把「剩下的幾分之幾」當成「全部的幾分之幾」了。\n→ 先算出第一步剩下多少，再用剩下的量做第二步。'
    },
    'unit_mismatch': {
      detect: function(q, wrongAns){
        return /單位|cm³|m³|公分|公尺|元|分鐘|小時|頁/.test(q.question) &&
               !/[a-zA-Z%㎡³元個頁]/.test(String(wrongAns));
      },
      remedy: '最後答案漏寫或寫錯單位了。\n→ 回到題目找出答案需要什麼單位，再補上。'
    },
    'percent_decimal_error': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'percent') return false;
        var correctNum = parseFloat(q.answer);
        var wrongNum = parseFloat(wrongAns);
        if (!isFinite(correctNum) || !isFinite(wrongNum)) return false;
        return Math.abs(wrongNum - correctNum * 10) < 0.01 || Math.abs(wrongNum - correctNum / 10) < 0.01;
      },
      remedy: '折數轉小數可能錯了。\n→ 記住：N 折 = N/10 = 0.N（例如 9折=0.9）。'
    },
    'direction_error': {
      detect: function(q, wrongAns){
        var correctNum = parseFloat(q.answer);
        var wrongNum = parseFloat(wrongAns);
        if (!isFinite(correctNum) || !isFinite(wrongNum)) return false;
        /* Wrong direction: addition instead of subtraction or vice versa */
        return (correctNum > 0 && wrongNum > 0 && Math.abs(wrongNum + correctNum) < correctNum * 0.1);
      },
      remedy: '運算方向可能反了（加↔減 或 乘↔除）。\n→ 回到題目：是「取走/用掉」→減法，還是「合在一起」→加法？'
    },
    'decimal_point_error': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'decimal') return false;
        var correctNum = parseFloat(q.answer);
        var wrongNum = parseFloat(wrongAns);
        if (!isFinite(correctNum) || !isFinite(wrongNum) || correctNum === 0) return false;
        var ratio = wrongNum / correctNum;
        return Math.abs(ratio - 10) < 0.01 || Math.abs(ratio - 100) < 0.01 ||
               Math.abs(ratio - 0.1) < 0.01 || Math.abs(ratio - 0.01) < 0.01;
      },
      remedy: '小數點位置可能放錯了。\n→ 乘法：小數位數相加；除法：對齊被除數的小數點往上點。'
    },
    'time_borrow_error': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'time') return false;
        return /^-?\d/.test(String(wrongAns));
      },
      remedy: '時間進位/借位可能出錯。\n→ 60 分鐘 = 1 小時；不夠減先從小時借 1 變成 60 分鐘。'
    },
    'fraction_not_reduced': {
      detect: function(q, wrongAns){
        /* Student got correct value but didn't simplify — check if wrong/correct are equivalent fractions */
        var fam = getFamily(q.kind);
        if (fam !== 'fracAdd' && fam !== 'fracWord' && fam !== 'fracRemain') return false;
        var aFracs = extractFractions(String(q.answer));
        var wFracs = extractFractions(String(wrongAns));
        if (aFracs.length !== 1 || wFracs.length !== 1) return false;
        var af = aFracs[0], wf = wFracs[0];
        /* Same value but different representation */
        if (af.den === 0 || wf.den === 0) return false;
        return (af.num * wf.den === wf.num * af.den) && (af.den !== wf.den || af.num !== wf.num);
      },
      remedy: '你的答案數值是對的，但分數還沒約到最簡分數。\n→ 找分子和分母的最大公因數（GCD），把分子分母同除以它。'
    },
    'volume_area_confusion': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'volume') return false;
        var ints2 = extractIntegers(q.question);
        if (ints2.length < 3) return false;
        var wrongNum = parseFloat(wrongAns);
        if (!isFinite(wrongNum)) return false;
        /* Check if student computed area instead of volume (or vice versa) */
        var area = ints2[0] * ints2[1];
        var vol = area * ints2[2];
        var correctNum = parseFloat(q.answer);
        if (correctNum === vol && Math.abs(wrongNum - area) < 0.01) return true;
        if (correctNum === area && Math.abs(wrongNum - vol) < 0.01) return true;
        return false;
      },
      remedy: '你可能搞混了「面積」和「體積」。\n→ 面積 = 長×寬（平方單位）；體積 = 長×寬×高（立方單位）。\n確認題目問的是面積還是體積。'
    },
    'forgot_second_step': {
      detect: function(q, wrongAns){
        /* Student only did the first step in a two-step problem */
        if (getFamily(q.kind) !== 'fracRemain') return false;
        var fracs2 = extractFractions(q.question);
        if (fracs2.length < 2) return false;
        var wrongNum = parseFloat(wrongAns);
        var f1 = fracs2[0];
        /* Check if student just computed 1 - first_fraction */
        var remainder = 1 - f1.num / f1.den;
        if (isFinite(remainder) && Math.abs(wrongNum - remainder) < 0.001) return true;
        /* Or just computed the first fraction */
        if (Math.abs(wrongNum - f1.num / f1.den) < 0.001) return true;
        return false;
      },
      remedy: '你可能只做了第一步就停了。\n→ 這題有兩段操作：先算出第一步結果，再對「剩下的量」做第二步。'
    },
    'sum_not_average': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'average') return false;
        var ints3 = extractIntegers(q.question);
        if (ints3.length < 2) return false;
        var wrongNum = parseFloat(wrongAns);
        var correctNum = parseFloat(q.answer);
        if (!isFinite(wrongNum) || !isFinite(correctNum)) return false;
        var sum = ints3.reduce(function(s,v){ return s+v; }, 0);
        /* Student gave sum instead of average */
        return Math.abs(wrongNum - sum) < 0.01 && Math.abs(correctNum - sum / ints3.length) < 0.01;
      },
      remedy: '你算出了總和，但忘記除以個數。\n→ 平均 = 總和 ÷ 個數，記得最後一步要除！'
    },
    'off_by_one': {
      detect: function(q, wrongAns){
        var correctNum = parseFloat(q.answer);
        var wrongNum = parseFloat(wrongAns);
        if (!isFinite(correctNum) || !isFinite(wrongNum)) return false;
        return Math.abs(wrongNum - correctNum) === 1;
      },
      remedy: '答案差了 1，可能是「包含端點」的計數錯誤。\n→ 數東西時注意：是否要「+1」（含左右兩端），或者進位時多了/少了 1。'
    },
    'numerator_denominator_swap': {
      detect: function(q, wrongAns){
        var fam = getFamily(q.kind);
        if (fam !== 'fracAdd' && fam !== 'fracWord' && fam !== 'fracRemain') return false;
        var aFracs = extractFractions(String(q.answer));
        var wFracs = extractFractions(String(wrongAns));
        if (aFracs.length !== 1 || wFracs.length !== 1) return false;
        var af = aFracs[0], wf = wFracs[0];
        /* Swapped: wrong num=correct den and wrong den=correct num */
        return af.num === wf.den && af.den === wf.num && af.num !== af.den;
      },
      remedy: '你可能把分子和分母寫反了。\n→ 分子在上（被取走的份數），分母在下（全部被平分的份數）。'
    },
    'forgot_borrow_60': {
      detect: function(q, wrongAns){
        if (getFamily(q.kind) !== 'time') return false;
        var timeRe = /(\d{1,2})\s*[:：時]\s*(\d{1,2})?/g;
        var times = [];
        var tm;
        while ((tm = timeRe.exec(q.question)) !== null){
          times.push({ h: parseInt(tm[1],10), m: parseInt(tm[2]||'0',10) });
        }
        if (times.length < 2 || times[1].m >= times[0].m) return false;
        /* Need borrow: check if student subtracted minutes directly (wrong) */
        var wrongMinMatch = String(wrongAns).match(/(\d+)\s*(?:時|:)\s*(\d+)/);
        if (!wrongMinMatch) return false;
        var wH = parseInt(wrongMinMatch[1],10);
        var wM = parseInt(wrongMinMatch[2],10);
        var expectedWrongH = times[1].h - times[0].h;
        var expectedWrongM = times[1].m - times[0].m; /* negative */
        return wH === expectedWrongH && wM === Math.abs(expectedWrongM);
      },
      remedy: '分鐘不夠減時需要借位！\n→ 從小時借 1 = 60 分鐘加到分鐘欄，小時欄減 1，再做減法。'
    }
  };

  function diagnoseWrongAnswer(q, wrongAns){
    if (!q || !wrongAns) return null;
    var results = [];
    for (var key in MISCONCEPTION_MAP){
      if (!MISCONCEPTION_MAP.hasOwnProperty(key)) continue;
      var m = MISCONCEPTION_MAP[key];
      try {
        if (m.detect(q, wrongAns)){
          results.push({ tag: key, remedy: m.remedy });
        }
      } catch(e){}
    }
    /* Also check common_wrong_answers from question data */
    if (Array.isArray(q.common_wrong_answers)){
      var wNorm = normalizeForCompare(wrongAns);
      for (var i = 0; i < q.common_wrong_answers.length; i++){
        if (normalizeForCompare(q.common_wrong_answers[i]) === wNorm){
          results.push({ tag: 'known_misconception', remedy: '這是常見錯誤答案。請回到提示重新審題，特別注意基準量與運算方向。' });
          break;
        }
      }
    }
    /* Base switch special */
    if (needsBaseSwitchWarning(q.question) && results.length === 0){
      results.push({ tag: 'base_switch_warning', remedy: MISCONCEPTION_MAP.base_switch_error.remedy });
    }
    return results.length ? results : null;
  }

  function extractFirstNumber(text){
    var m = String(text || '').match(/\d+(?:\.\d+)?/);
    return m ? parseFloat(m[0]) : null;
  }

  /* ============================================================
   * 5. 視覺提示分級 — 四級 (v2)
   * ============================================================ */
  function getHintTier(level){
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    return TIER_DEFS[lv-1] || TIER_DEFS[0];
  }

  function formatHintWithTier(hintText, level, q){
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    var t = getHintTier(lv);
    var header = t.icon + '【Level ' + lv + '｜' + t.label + '】';
    var body = String(hintText || '');

    /* Base switch reminder injection (all levels) */
    if (q && needsBaseSwitchWarning(q.question)){
      var reminder = getBaseSwitchReminder(q.question);
      if (reminder && body.indexOf('基準切換') === -1 && body.indexOf('基準量切換') === -1){
        body = body + '\n' + reminder;
      }
    }

    return header + '\n' + body;
  }

  /* ============================================================
   * 6. 提示成效閉環 — 記錄看到哪層後答對
   * ============================================================ */
  var _tracking = null;

  function _loadTracking(){
    if (_tracking) return _tracking;
    try {
      _tracking = JSON.parse(localStorage.getItem(TRACK_KEY) || '{}');
    } catch(e){
      _tracking = {};
    }
    return _tracking;
  }

  function _saveTracking(){
    if (!_tracking) return;
    try {
      /* Keep size bounded: only last 500 entries */
      var keys = Object.keys(_tracking);
      if (keys.length > 500){
        var sorted = keys.map(function(k){ return { k:k, ts:_tracking[k].ts||0 }; })
                         .sort(function(a,b){ return a.ts - b.ts; });
        for (var i = 0; i < sorted.length - 500; i++){
          delete _tracking[sorted[i].k];
        }
      }
      localStorage.setItem(TRACK_KEY, JSON.stringify(_tracking));
    } catch(e){}
  }

  /**
   * recordHintUsage(questionId, maxHintLevel, isCorrect)
   * Call after student submits answer.
   */
  function recordHintUsage(questionId, maxHintLevel, isCorrect){
    var data = _loadTracking();
    var id = String(questionId || 'unknown');
    if (!data[id]) data[id] = { attempts: 0, correctAfterHint: {}, totalHint: {} };
    var rec = data[id];
    rec.attempts = (rec.attempts || 0) + 1;
    rec.ts = Date.now();
    rec.lastTs = rec.ts;
    rec.lastCorrect = !!isCorrect;
    var lvKey = 'L' + Math.max(0, Math.min(4, Number(maxHintLevel) || 0));
    rec.totalHint[lvKey] = (rec.totalHint[lvKey] || 0) + 1;
    if (isCorrect){
      rec.correctAfterHint[lvKey] = (rec.correctAfterHint[lvKey] || 0) + 1;
    }
    _saveTracking();
  }

  /**
   * getHintEffectivenessReport()
   * Returns { highDependency: [...], summary: {...} }
   */
  function getHintEffectivenessReport(){
    var data = _loadTracking();
    var items = [];
    for (var id in data){
      if (!data.hasOwnProperty(id)) continue;
      var rec = data[id];
      var total = rec.attempts || 0;
      var correctL0 = (rec.correctAfterHint && rec.correctAfterHint.L0) || 0;
      var correctL1 = (rec.correctAfterHint && rec.correctAfterHint.L1) || 0;
      var correctL2 = (rec.correctAfterHint && rec.correctAfterHint.L2) || 0;
      var correctL3 = (rec.correctAfterHint && rec.correctAfterHint.L3) || 0;
      var correctL4 = (rec.correctAfterHint && rec.correctAfterHint.L4) || 0;
      var hintNeeded = total - correctL0; /* attempts that needed at least L1 */
      var dependency = total > 0 ? (hintNeeded / total) : 0;
      items.push({
        id: id,
        total: total,
        correctNoHint: correctL0,
        correctL1: correctL1,
        correctL2: correctL2,
        correctL3: correctL3,
        correctL4: correctL4,
        dependencyRatio: Math.round(dependency * 100)
      });
    }
    items.sort(function(a,b){ return b.dependencyRatio - a.dependencyRatio; });
    var highDep = items.filter(function(it){ return it.dependencyRatio >= 70 && it.total >= 2; });
    return {
      highDependency: highDep.slice(0, 20),
      totalTracked: items.length,
      summary: {
        avgDependency: items.length ? Math.round(items.reduce(function(s,i){ return s + i.dependencyRatio; },0) / items.length) : 0
      }
    };
  }

  /* ============================================================
   * 6b. Misconception retry tracking
   * ============================================================ */
  var DIAG_TRACK_KEY = 'aimath.diagTracking';
  var _diagTracking = null;

  function _loadDiagTracking(){
    if (_diagTracking) return _diagTracking;
    try {
      _diagTracking = JSON.parse(localStorage.getItem(DIAG_TRACK_KEY) || '{}');
    } catch(e){
      _diagTracking = {};
    }
    return _diagTracking;
  }

  function _saveDiagTracking(){
    if (!_diagTracking) return;
    try {
      var keys = Object.keys(_diagTracking);
      if (keys.length > 300){
        var sorted = keys.map(function(k){ return { k:k, ts:_diagTracking[k].ts||0 }; })
                         .sort(function(a,b){ return a.ts - b.ts; });
        for (var i = 0; i < sorted.length - 300; i++){
          delete _diagTracking[sorted[i].k];
        }
      }
      localStorage.setItem(DIAG_TRACK_KEY, JSON.stringify(_diagTracking));
    } catch(e){}
  }

  /**
   * recordMisconception(questionId, tags)
   * Record which misconception tags were triggered for a question.
   */
  function recordMisconception(questionId, tags){
    var data = _loadDiagTracking();
    var id = String(questionId || 'unknown');
    if (!data[id]) data[id] = { triggers: [], corrected: false, ts: Date.now() };
    var rec = data[id];
    rec.ts = Date.now();
    for (var i = 0; i < tags.length; i++){
      if (rec.triggers.indexOf(tags[i]) === -1) rec.triggers.push(tags[i]);
    }
    rec.corrected = false;
    _saveDiagTracking();
  }

  /**
   * recordMisconceptionCorrected(questionId)
   * Mark that the student got it right after diagnosis.
   */
  function recordMisconceptionCorrected(questionId){
    var data = _loadDiagTracking();
    var id = String(questionId || 'unknown');
    if (data[id]){
      data[id].corrected = true;
      data[id].ts = Date.now();
      _saveDiagTracking();
    }
  }

  /**
   * getMisconceptionReport()
   * Returns { frequent: [...], correctionRate: Number }
   */
  function getMisconceptionReport(){
    var data = _loadDiagTracking();
    var tagCounts = {};
    var totalTriggered = 0;
    var totalCorrected = 0;
    for (var id in data){
      if (!data.hasOwnProperty(id)) continue;
      var rec = data[id];
      totalTriggered++;
      if (rec.corrected) totalCorrected++;
      for (var t = 0; t < (rec.triggers || []).length; t++){
        var tag = rec.triggers[t];
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      }
    }
    var frequent = [];
    for (var key in tagCounts){
      if (!tagCounts.hasOwnProperty(key)) continue;
      frequent.push({ tag: key, count: tagCounts[key] });
    }
    frequent.sort(function(a,b){ return b.count - a.count; });
    /* Per-family breakdown */
    var familyCounts = {};
    for (var fid in data){
      if (!data.hasOwnProperty(fid)) continue;
      var frec = data[fid];
      /* Extract family from question id pattern (module_kind_nnn) */
      var fParts = String(fid).split('_');
      var fKey = fParts.length >= 2 ? fParts.slice(0, -1).join('_') : 'unknown';
      if (!familyCounts[fKey]) familyCounts[fKey] = { triggered: 0, corrected: 0 };
      familyCounts[fKey].triggered++;
      if (frec.corrected) familyCounts[fKey].corrected++;
    }

    return {
      frequent: frequent.slice(0, 15),
      totalTriggered: totalTriggered,
      totalCorrected: totalCorrected,
      correctionRate: totalTriggered > 0 ? Math.round(totalCorrected / totalTriggered * 100) : 0,
      byFamily: familyCounts,
      topMisconceptions: frequent.slice(0, 3).map(function(f){
        var names = {
          base_switch_error: '基準量搞混',
          unit_mismatch: '單位漏寫/錯誤',
          percent_decimal_error: '折數↔小數轉換錯',
          direction_error: '加減方向反',
          decimal_point_error: '小數點位置錯',
          time_borrow_error: '時間借位錯',
          fraction_not_reduced: '分數未約分',
          volume_area_confusion: '面積↔體積搞混',
          forgot_second_step: '兩步題只做一步',
          sum_not_average: '只算總和忘除',
          off_by_one: '差一錯誤',
          numerator_denominator_swap: '分子分母寫反',
          forgot_borrow_60: '時間忘借位60分'
        };
        return { tag: f.tag, name: names[f.tag] || f.tag, count: f.count };
      })
    };
  }

  /**
   * suggestHintLevel(questionId)
   * Based on past hint usage and misconceptions, suggest which hint level
   * the student should start with for this question.
   * Returns { level: 1-4, reason: String }
   */
  function suggestHintLevel(questionId){
    var id = String(questionId || '');
    var hData = _loadTracking();
    var dData = _loadDiagTracking();
    var rec = hData[id];
    var dRec = dData[id];

    /* Calculate recent wrong streak across all questions */
    var streak = _getRecentWrongStreak(hData);

    /* Has prior misconceptions that weren't corrected — suggest L2 */
    if (dRec && dRec.triggers && dRec.triggers.length > 0 && !dRec.corrected){
      return { level: 2, reason: '上次有錯因（' + dRec.triggers[0] + '），建議從畫圖確認' };
    }

    /* First attempt: if on a hot streak of wrongs, bump up */
    if (!rec || !rec.attempts || rec.attempts === 0){
      if (streak >= 3){
        return { level: 2, reason: '連續 ' + streak + ' 題答錯，建議從畫圖確認' };
      }
      return { level: 1, reason: '初次作答，從觀念鎖定開始' };
    }

    /* Multiple attempts needed L3+ hints to succeed */
    var l3plus = (rec.correctAfterHint && ((rec.correctAfterHint.L3 || 0) + (rec.correctAfterHint.L4 || 0))) || 0;
    if (l3plus >= 2){
      return { level: 3, reason: '多次需要 L3+ 提示才答對，建議從讀圖階段開始' };
    }

    /* Streak-based escalation for returning question */
    if (streak >= 5){
      return { level: 2, reason: '連錯 ' + streak + ' 題，建議從畫圖重新確認觀念' };
    }

    /* Has been seen but not a hard question */
    return { level: 1, reason: '複習題目，從觀念鎖定開始' };
  }

  /**
   * _getRecentWrongStreak(hData)
   * Returns the number of consecutive most-recent wrong answers across all questions.
   */
  function _getRecentWrongStreak(hData){
    var entries = [];
    for (var k in hData){
      if (!hData.hasOwnProperty(k)) continue;
      var r = hData[k];
      if (r && r.lastTs && typeof r.lastCorrect === 'boolean'){
        entries.push({ ts: r.lastTs, correct: r.lastCorrect });
      }
    }
    if (entries.length === 0) return 0;
    entries.sort(function(a,b){ return b.ts - a.ts; });
    var streak = 0;
    for (var i = 0; i < entries.length; i++){
      if (!entries[i].correct) streak++;
      else break;
    }
    return streak;
  }

  /* ============================================================
   * Public API — processHint()
   * ============================================================
   * Main entry point. Takes raw hint text + question + level.
   * Returns enhanced hint string ready for display.
   * v2: supports 4 levels.
   */
  function processHint(rawHint, q, level){
    if (!isEnabled()) return rawHint;
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    var text = String(rawHint || '');

    /* If raw hint is empty/boilerplate, use template */
    if (!text.trim() || isBoilerplate(text)){
      text = getTemplatedHint(q, lv);
    }

    /* L4 anti-leak gate (was L3 in v1) */
    if (lv >= 4 && q){
      text = enforceL3Gate(text, q);
    }

    /* Format with tier decoration */
    text = formatHintWithTier(text, lv, q);

    return text;
  }

  /**
   * processHintHTML(q, level) — returns rich HTML hint with SVG visuals.
   * Call this for enhanced rendering; falls back to processHint() text.
   */
  function processHintHTML(q, level){
    if (!isEnabled()) return '';
    var lv = Math.max(1, Math.min(4, Number(level) || 1));
    var richHTML = buildRichHintHTML(q, lv);
    if (richHTML) return richHTML;
    /* Fallback to text template */
    return '<div>' + escapeHTML(processHint('', q, lv)).replace(/\n/g, '<br>') + '</div>';
  }

  function isBoilerplate(text){
    var t = String(text || '');
    return /請依前面步驟完成計算|最後請自行寫出答案|^[\s（）()]*$/.test(t);
  }

  /* ============================================================
   * Auto-integration: DOM hooks for hint enhancement + tracking
   * ============================================================ */
  var _currentQ = null;  /* set by page via setCurrentQuestion() */
  var _maxHintLv = 0;
  var _moduleId = '';
  var _observer = null;

  function setCurrentQuestion(q){
    _currentQ = q || null;
    _maxHintLv = 0;
  }

  /** Post-process a hint DOM node: add tier label, base-switch, L4 gate, SVG visuals */
  function enhanceHintNode(node){
    if (!node || node.dataset.heProcessed) return;
    node.dataset.heProcessed = '1';
    var text = node.textContent || '';
    if (!text.trim()) return;

    var q = _currentQ;
    /* Detect hint level from node dataset, class, or text prefix */
    var lv = 0;
    if (node.dataset.level) lv = Number(node.dataset.level);
    else {
      var m = text.match(/(?:Level|提示|Hint)\s*(\d)/i);
      if (m) lv = Number(m[1]);
      else {
        /* Infer from content stage */
        if (/觀念|重點|先想|先圈/.test(text)) lv = 1;
        else if (/畫圖|畫一|圖像|長條|數線|bar|SVG/i.test(text)) lv = 2;
        else if (/讀圖|數格|格子|grid/i.test(text)) lv = 3;
        else if (/列式|做法|算式|步驟|完成計算|檢查|收尾/.test(text)) lv = 4;
        else lv = 1;
      }
    }
    if (lv > 0) _maxHintLv = Math.max(_maxHintLv, lv);

    /* --- L4 anti-leak gate (was L3) --- */
    if (lv >= 4 && q){
      var cleaned = enforceL3Gate(text, q);
      if (cleaned !== text){
        node.textContent = cleaned;
        text = cleaned;
      }
    }

    /* --- Add tier visual badge --- */
    var tier = getHintTier(lv);
    if (!node.querySelector('.he-badge')){
      var badge = document.createElement('span');
      badge.className = 'he-badge';
      badge.style.cssText = 'display:inline-block;font-size:11px;padding:2px 8px;border-radius:4px;margin-right:6px;margin-bottom:4px;font-weight:700;background:' + tier.bg + ';color:' + tier.color;
      badge.textContent = tier.icon + ' ' + tier.label;
      node.insertBefore(badge, node.firstChild);
    }

    /* --- Inject rich SVG visual if applicable --- */
    if (q && (lv === 2 || lv === 3)){
      var richHTML = buildRichHintHTML(q, lv);
      if (richHTML && !node.querySelector('.he-rich-viz')){
        var vizWrap = document.createElement('div');
        vizWrap.className = 'he-rich-viz';
        vizWrap.innerHTML = richHTML;
        node.appendChild(vizWrap);
      }
    }

    /* --- Base switch warning injection --- */
    if (q && needsBaseSwitchWarning(q.question)){
      var existing = node.textContent || '';
      if (existing.indexOf('基準切換') === -1 && existing.indexOf('基準量切換') === -1){
        var warn = document.createElement('div');
        warn.className = 'he-base-switch';
        warn.textContent = getBaseSwitchReminder(q.question);
        node.appendChild(warn);
      }
    }

    /* --- L4 sanity check prompt --- */
    if (lv === 4){
      if ((node.textContent || '').indexOf('填入你的答案') === -1){
        var finDiv = document.createElement('div');
        finDiv.className = 'he-finish';
        finDiv.textContent = '🏁 填入你的答案';
        node.appendChild(finDiv);
      }
    }
  }

  /** Observe #hints container for new hint nodes */
  function observeHints(){
    var containers = document.querySelectorAll('#hints, #hintBox, .hints');
    if (!containers.length) return;

    if (_observer) _observer.disconnect();
    _observer = new MutationObserver(function(mutations){
      for (var i = 0; i < mutations.length; i++){
        var mut = mutations[i];
        for (var j = 0; j < mut.addedNodes.length; j++){
          var n = mut.addedNodes[j];
          if (n.nodeType === 1 && (n.classList.contains('hint') || n.classList.contains('hint-ladder-card'))){
            enhanceHintNode(n);
          }
          /* Also check child .hint elements */
          if (n.nodeType === 1 && n.querySelectorAll){
            var kids = n.querySelectorAll('.hint, .hint-ladder-card');
            for (var k = 0; k < kids.length; k++) enhanceHintNode(kids[k]);
          }
        }
        /* Text content change on #hintBox */
        if (mut.type === 'characterData' || (mut.type === 'childList' && mut.target.id === 'hintBox')){
          enhanceHintNode(mut.target);
        }
      }
    });

    for (var c = 0; c < containers.length; c++){
      _observer.observe(containers[c], { childList: true, subtree: true, characterData: true });
    }
  }

  /** Hook btnCheck for answer tracking + wrong-answer diagnosis */
  function hookAnswerCheck(){
    var btnCheck = document.getElementById('btnCheck') || document.getElementById('btnSubmit');
    if (!btnCheck || btnCheck.dataset.heHooked) return;
    btnCheck.dataset.heHooked = '1';

    btnCheck.addEventListener('click', function(){
      setTimeout(function(){
        var q = _currentQ;
        if (!q) return;

        var banner = document.getElementById('banner');
        var bannerText = (banner && banner.textContent) || '';
        var isCorrect = banner && (/\bgood\b/.test(banner.className) || /正確|答對|✓/.test(bannerText));
        var isBad = banner && (/\bbad\b/.test(banner.className) || /再想想|不對|錯誤/.test(bannerText));

        /* Track hint effectiveness */
        recordHintUsage(q.id, _maxHintLv, !!isCorrect);

        /* If correct and previously had misconception, mark corrected */
        if (isCorrect){
          recordMisconceptionCorrected(q.id);
        }

        /* Wrong-answer diagnosis */
        if (isBad){
          var ansInput = document.getElementById('answer') || document.getElementById('ans') || document.getElementById('gAnswer');
          var wrongAns = ansInput ? ansInput.value : '';
          var diagnosis = diagnoseWrongAnswer(q, wrongAns);
          if (diagnosis && diagnosis.length > 0){
            var diagTags = diagnosis.map(function(d){ return d.tag; });
            recordMisconception(q.id, diagTags);
            showDiagnosisUI(diagnosis);
          }
        }
      }, 200); /* Wait for page's own check handler to set banner */
    }, true); /* Capture phase to run after native handler */
  }

  /* Tag → emoji icon mapping for diagnosis UI */
  var DIAG_ICONS = {
    base_switch_error: '🔄', unit_mismatch: '📏', percent_decimal_error: '🔢',
    direction_error: '↕️', decimal_point_error: '🔵', time_borrow_error: '⏰',
    fraction_not_reduced: '✂️', volume_area_confusion: '📦', forgot_second_step: '⏩',
    sum_not_average: '➗', off_by_one: '1️⃣', known_misconception: '⚠️',
    base_switch_warning: '🔄'
  };
  var DIAG_SEVERITY = {
    base_switch_error: 'high', direction_error: 'high', forgot_second_step: 'high',
    decimal_point_error: 'med', percent_decimal_error: 'med', time_borrow_error: 'med',
    volume_area_confusion: 'med', sum_not_average: 'med',
    fraction_not_reduced: 'low', off_by_one: 'low', known_misconception: 'med',
    base_switch_warning: 'low'
  };

  function showDiagnosisUI(diagList){
    /* Remove previous diagnosis */
    var old = document.getElementById('heDiagnosis');
    if (old) old.remove();

    var container = document.getElementById('hints') || document.getElementById('banner');
    if (!container || !container.parentElement) return;

    var wrap = document.createElement('div');
    wrap.id = 'heDiagnosis';
    wrap.className = 'he-diag';

    /* Header with icon */
    var header = document.createElement('div');
    header.className = 'he-diag-header';
    header.innerHTML = '<span class="he-diag-icon">🔎</span> <span class="he-diag-tag">錯因診斷</span>';
    wrap.appendChild(header);

    /* Diagnosis cards */
    for (var i = 0; i < Math.min(diagList.length, 3); i++){
      var d = diagList[i];
      var card = document.createElement('div');
      var sev = DIAG_SEVERITY[d.tag] || 'med';
      card.className = 'he-diag-card he-diag-sev-' + sev;
      card.style.animationDelay = (i * 0.12) + 's';

      /* Tag badge */
      var badge = document.createElement('span');
      badge.className = 'he-diag-badge';
      var icon = DIAG_ICONS[d.tag] || '❓';
      var tagLabel = d.tag.replace(/_/g, ' ');
      badge.textContent = icon + ' ' + tagLabel;
      card.appendChild(badge);

      /* Remedy text */
      var remedyDiv = document.createElement('div');
      remedyDiv.className = 'he-diag-remedy';
      /* Split remedy into lines for readability */
      var lines = d.remedy.split('\n');
      for (var li = 0; li < lines.length; li++){
        if (li > 0) remedyDiv.appendChild(document.createElement('br'));
        remedyDiv.appendChild(document.createTextNode(lines[li]));
      }
      card.appendChild(remedyDiv);

      wrap.appendChild(card);
    }

    /* Retry button */
    var retryBtn = document.createElement('button');
    retryBtn.className = 'he-diag-retry';
    retryBtn.textContent = '🔁 再試一次';
    retryBtn.addEventListener('click', function(){
      var ansInput = document.getElementById('answer') || document.getElementById('ans') || document.getElementById('gAnswer');
      if (ansInput){
        ansInput.value = '';
        ansInput.focus();
      }
      var diagEl = document.getElementById('heDiagnosis');
      if (diagEl) diagEl.remove();
    });
    wrap.appendChild(retryBtn);

    container.parentElement.insertBefore(wrap, container.nextSibling);
  }

  /** Hook boilerplate hint replacement: intercept before render */
  function hookHintButtons(){
    /* For pages with #hintLevel dropdown + #btnHint button */
    var btnHint = document.getElementById('btnHint');
    if (btnHint && !btnHint.dataset.heHooked){
      btnHint.dataset.heHooked = '1';
      btnHint.addEventListener('click', function(){
        var sel = document.getElementById('hintLevel');
        var lv = sel ? Number(sel.value) : 1;
        _maxHintLv = Math.max(_maxHintLv, lv);
      }, true);
    }

    /* For pages with #btnHint1, #btnHint2, #btnHint3 */
    for (var i = 1; i <= 4; i++){
      (function(level){
        var btn = document.getElementById('btnHint' + level);
        if (btn && !btn.dataset.heHooked){
          btn.dataset.heHooked = '1';
          btn.addEventListener('click', function(){
            _maxHintLv = Math.max(_maxHintLv, level);
          }, true);
        }
      })(i);
    }
  }

  /* ============================================================
   * init() — auto-inject styles + auto-hook DOM
   * ============================================================ */
  function injectStyle(){
    if (document.getElementById('hintEngineStyle')) return;
    var st = document.createElement('style');
    st.id = 'hintEngineStyle';
    st.textContent = [
      /* Base switch warning */
      '.he-base-switch{color:#ffe3b0;font-weight:700;border-left:3px solid #f0b429;padding-left:6px;margin:6px 0;font-size:12px}',
      /* Badge */
      '.he-badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:4px;margin-right:6px;margin-bottom:4px;font-weight:700}',
      /* Diagnosis */
      '.he-diag{margin-top:8px;border:1px solid rgba(248,81,73,.35);border-radius:10px;padding:10px 12px;background:rgba(248,81,73,.06);animation:heDiagSlideIn .4s ease-out}',
      '@keyframes heDiagSlideIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}',
      '.he-diag-header{display:flex;align-items:center;gap:6px;margin-bottom:8px}',
      '.he-diag-icon{font-size:18px}',
      '.he-diag-tag{font-weight:800;color:#ffd2cf;font-size:14px}',
      '.he-diag-card{margin:6px 0;padding:8px 10px;border-radius:8px;border-left:3px solid #6b7280;background:rgba(255,255,255,.03);animation:heDiagSlideIn .4s ease-out both}',
      '.he-diag-sev-high{border-left-color:#f85149;background:rgba(248,81,73,.08)}',
      '.he-diag-sev-med{border-left-color:#d29922;background:rgba(210,153,34,.06)}',
      '.he-diag-sev-low{border-left-color:#3fb950;background:rgba(63,185,80,.05)}',
      '.he-diag-badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:4px;background:rgba(255,255,255,.08);color:#e5e7eb;font-weight:700;margin-bottom:4px}',
      '.he-diag-remedy{margin-top:4px;color:#c9d1d9;font-size:13px;line-height:1.6}',
      '.he-diag-retry{display:block;margin:10px auto 2px;padding:6px 18px;border:1px solid rgba(88,166,255,.4);border-radius:6px;background:rgba(88,166,255,.1);color:#58a6ff;font-weight:700;font-size:13px;cursor:pointer;transition:background .2s}',
      '.he-diag-retry:hover{background:rgba(88,166,255,.2)}',
      /* Report */
      '.he-report{margin-top:10px;font-size:12px;border:1px solid rgba(88,166,255,.25);border-radius:8px;padding:8px;background:rgba(88,166,255,.05)}',
      /* Rich hint levels */
      '.he-rich-l1{color:#58a6ff;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l2{color:#3fb950;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l3{color:#d29922;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l4{color:#f85149;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-viz{margin:6px 0;animation:heVizFadeIn .5s ease-out}',
      '@keyframes heVizFadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}',
      /* SVG specific animations */
      '.he-rich-viz svg{transition:opacity .3s ease}',
      '.he-rich-viz svg:hover{opacity:.85}',
      /* Formula scaffolding */
      '.he-formula{background:rgba(210,153,34,.1);border:1px solid rgba(210,153,34,.3);border-radius:6px;padding:6px 10px;margin:6px 0;font-family:monospace;font-size:13px;color:#e5e7eb;line-height:1.7}',
      '.he-step-row{margin:3px 0;padding:2px 0;border-bottom:1px dotted rgba(210,153,34,.15)}',
      '.he-step-row:last-child{border-bottom:none}',
      '.he-placeholder{display:inline-block;width:22px;height:18px;border:2px dashed #d29922;border-radius:3px;text-align:center;color:#d29922;font-weight:900;font-size:14px;vertical-align:middle;line-height:18px;margin:0 2px}',
      /* Check indicators */
      '.he-check-ok{color:#3fb950;font-size:12px;margin:2px 0}',
      '.he-check-bad{color:#f85149;font-size:12px;margin:2px 0}',
      /* Finish prompt */
      '.he-finish{color:#d29922;font-weight:700;font-size:13px;margin-top:8px;padding:4px 8px;border:1px dashed rgba(210,153,34,.5);border-radius:4px;display:inline-block}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function init(config){
    if (!isEnabled()) return;
    config = config || {};
    _moduleId = config.moduleId || '';
    injectStyle();
    _loadTracking();
    /* Auto-hook after a short delay to let page init complete */
    setTimeout(function(){
      observeHints();
      hookAnswerCheck();
      hookHintButtons();
    }, 300);
  }

  /* Expose */
  window.AIMathHintEngine = {
    init: init,
    isEnabled: isEnabled,
    enable: function(){ localStorage.setItem(ENABLE_KEY, '1'); },
    disable: function(){ localStorage.setItem(ENABLE_KEY, '0'); },

    /* Core */
    processHint: processHint,
    processHintHTML: processHintHTML,
    buildRichHintHTML: buildRichHintHTML,
    getTemplatedHint: getTemplatedHint,
    getFamily: getFamily,
    getHintTier: getHintTier,
    formatHintWithTier: formatHintWithTier,

    /* SVG generators */
    buildFractionBarSVG: buildFractionBarSVG,
    buildGridSVG: buildGridSVG,
    buildNumberLineSVG: buildNumberLineSVG,
    buildPercentGridSVG: buildPercentGridSVG,
    buildClockFaceSVG: buildClockFaceSVG,
    buildIsometricBoxSVG: buildIsometricBoxSVG,
    buildLevelingSVG: buildLevelingSVG,
    buildNumberBondSVG: buildNumberBondSVG,
    buildPlaceValueSVG: buildPlaceValueSVG,
    buildComparisonBarSVG: buildComparisonBarSVG,
    buildStepIndicatorSVG: buildStepIndicatorSVG,
    buildFractionCircleSVG: buildFractionCircleSVG,
    buildTreeDiagramSVG: buildTreeDiagramSVG,
    buildAreaModelSVG: buildAreaModelSVG,
    buildTapeModelSVG: buildTapeModelSVG,
    buildFractionComparisonSVG: buildFractionComparisonSVG,
    buildProgressRingSVG: buildProgressRingSVG,
    buildBarChartSVG: buildBarChartSVG,
    buildDotPlotSVG: buildDotPlotSVG,
    highlightKeywords: highlightKeywords,

    /* L4 gate */
    enforceL3Gate: enforceL3Gate,
    stripAnswerFromHint: stripAnswerFromHint,

    /* Base switch */
    needsBaseSwitchWarning: needsBaseSwitchWarning,
    getBaseSwitchReminder: getBaseSwitchReminder,

    /* Error diagnosis */
    diagnoseWrongAnswer: diagnoseWrongAnswer,

    /* Tracking */
    recordHintUsage: recordHintUsage,
    getHintEffectivenessReport: getHintEffectivenessReport,
    recordMisconception: recordMisconception,
    recordMisconceptionCorrected: recordMisconceptionCorrected,
    getMisconceptionReport: getMisconceptionReport,
    suggestHintLevel: suggestHintLevel,

    /* Utilities */
    extractFractions: extractFractions,
    extractIntegers: extractIntegers,

    /* Page integration */
    setCurrentQuestion: setCurrentQuestion
  };

})();
