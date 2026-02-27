/**
 * hint_engine.js — 全站提示優化引擎 v2
 *
 * 四級視覺鷹架系統：
 *  L1 觀念鎖定 — 圈重點、辨題型、基準切換警示
 *  L2 畫圖     — 動態 SVG 長條圖/數線/百格/3D 盒
 *  L3 讀圖得分數 — 格子圖 + 色塊對應分數 + 驗證加總
 *  L4 算式收斂 + 合理性檢查 — 分步公式 + ✅/❌ 檢核
 *
 * 額外功能：
 *  • L4 嚴格防洩漏（只到中間量，不給最終答案）
 *  • 錯因對應提示（MISCONCEPTION_MAP → 補救句）
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
    /* Match patterns: a/b, a／b, b分之a */
    var re1 = /(\d+)\s*[\/／]\s*(\d+)/g;
    var m;
    while ((m = re1.exec(t)) !== null){
      results.push({ num: parseInt(m[1],10), den: parseInt(m[2],10) });
    }
    var re2 = /(\d+)\s*分之\s*(\d+)/g;
    while ((m = re2.exec(t)) !== null){
      results.push({ num: parseInt(m[2],10), den: parseInt(m[1],10) });
    }
    return results;
  }
  function extractIntegers(text){
    var results = [];
    var t = String(text || '').replace(/\d+\s*[\/／分]\s*[之]?\s*\d+/g, ''); /* strip fractions */
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
  ['fraction_addsub','add_unlike','sub_unlike','fraction_add_unlike','fraction_sub_mixed','u2_frac_addsub_life'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracAdd'; });
  /* fracWord */
  ['fraction_of_quantity','reverse_fraction','average_division','generic_fraction_word','fraction_mul','mul','u1_avg_fraction','u3_frac_times_int'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracWord'; });
  /* fracRemain (two-step remainder) */
  ['remaining_after_fraction','remain_then_fraction','fraction_remaining','remaining_by_fraction','fraction_of_fraction'].forEach(function(k){ KIND_TO_FAMILY[k] = 'fracRemain'; });
  /* decimal */
  ['d_mul_d','d_div_int','d_mul_int','int_mul_d','int_div_int_to_decimal','decimal_mul','decimal_div','decimal_times_decimal','x10_shift','u6_frac_dec_convert','u9_unit_convert_decimal'].forEach(function(k){ KIND_TO_FAMILY[k] = 'decimal'; });
  /* percent */
  ['percent_of','percent_find_whole','percent_increase_decrease','percent_interest','ratio_missing_to_1','ratio_sub_decimal','discount'].forEach(function(k){ KIND_TO_FAMILY[k] = 'percent'; });
  /* time */
  ['time_add','time_add_cross_day','time_sub_cross_day'].forEach(function(k){ KIND_TO_FAMILY[k] = 'time'; });
  /* volume */
  ['rect_cm3','composite','composite3','rect_find_height','cube_find_edge','cm3_to_m3','m3_to_cm3','surface_area_rect_prism','area_tiling','decimal_dims','mixed_units','volume_rect_prism'].forEach(function(k){ KIND_TO_FAMILY[k] = 'volume'; });
  /* average */
  ['shopping_two_step','general'].forEach(function(k){ KIND_TO_FAMILY[k] = 'average'; });

  function getFamily(kind){
    return KIND_TO_FAMILY[String(kind || '')] || 'generic';
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

    var svg = '<svg width="'+W+'" height="'+(H+24)+'" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:6px auto">';

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

      /* Color first fraction (consumed) */
      for (var i = 0; i < Math.round(parts1); i++){
        svg += '<rect x="'+(i*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="'+colors[0]+'" opacity="0.7"/>';
      }

      /* Color second fraction (consumed from remainder) */
      var start2 = Math.round(parts1);
      for (var j = 0; j < Math.round(parts2); j++){
        svg += '<rect x="'+((start2+j)*partW+0.5)+'" y="0.5" width="'+(partW-1)+'" height="'+(H-1)+'" fill="'+colors[1]+'" opacity="0.7"/>';
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
    var svg = '<svg width="'+(W+2)+'" height="'+(H+30)+'" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:6px auto">';

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

    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:6px auto">';
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

  /* ============================================================
   * 2c. Rich Hint HTML Builder — per-family parametric hints
   * ============================================================ */

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

    /* --- L1: 觀念鎖定 (all families) --- */
    if (lv === 1){
      html += '<div class="he-rich-l1">' + escapeHTML(tpl.L1).replace(/\n/g, '<br>') + '</div>';
      if (family === 'fracRemain' || needsBaseSwitchWarning(text)){
        html += '<div class="he-base-switch">⚠️ 基準量切換：第二次操作不是對「全部」，而是對「前一步剩下的量」。</div>';
      }
      return html;
    }

    /* --- L2: 畫圖 (SVG diagrams) --- */
    if (lv === 2){
      html += '<div class="he-rich-l2">' + escapeHTML(tpl.L2).replace(/\n/g, '<br>') + '</div>';

      if ((family === 'fracRemain' || family === 'fracWord') && fracs.length >= 1){
        html += buildFractionBarSVG(fracs);
      } else if (family === 'fracAdd' && fracs.length >= 1){
        /* Show separate bars for comparison */
        for (var fi = 0; fi < Math.min(fracs.length, 3); fi++){
          html += buildFractionBarSVG([fracs[fi]], { width: 280, height: 30, colors: [['#ef4444','#3b82f6','#22c55e'][fi]] });
        }
      } else if (family === 'percent'){
        var pVal = 0;
        var m = text.match(/(\d+)\s*[%％折]/);
        if (m) pVal = parseInt(m[1], 10);
        if (/折/.test(text)) pVal = pVal * 10;
        if (pVal > 0 && pVal <= 100) html += buildPercentGridSVG(pVal);
      } else if (family === 'decimal'){
        var decs = [];
        var dm = text.match(/\d+\.\d+/g);
        if (dm) for (var di = 0; di < dm.length; di++) decs.push(parseFloat(dm[di]));
        if (decs.length > 0) html += buildNumberLineSVG(decs);
      } else if (family === 'volume' && ints.length >= 2){
        /* Simple 3D box representation */
        html += '<div style="font-size:12px;color:#e5e7eb;margin:4px 0">📦 長=' + ints[0] + ' 寬=' + (ints[1]||'?') + (ints.length > 2 ? ' 高=' + ints[2] : '') + '</div>';
      }

      if (needsBaseSwitchWarning(text)){
        html += '<div class="he-base-switch">⚠️ 注意：圖中第二段的顏色是從「剩下」的部分切出來的！</div>';
      }
      return html;
    }

    /* --- L3: 讀圖得分數 (grid + labels) --- */
    if (lv === 3){
      html += '<div class="he-rich-l3">' + escapeHTML(tpl.L3).replace(/\n/g, '<br>') + '</div>';

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
          html += '<div style="font-size:11px;color:#9ca3af;margin:2px 0">每格 = 1/'+totalCells+'　驗證：'+Math.round(cells1)+' + '+Math.round(cells2)+' + '+Math.round(cellsLeft)+' = '+totalCells+' ✓</div>';
        } else if (fracs.length === 1){
          var f = fracs[0];
          var gc = Math.min(f.den, 10);
          var gr = Math.ceil(f.den / gc);
          html += buildGridSVG(gr, gc, [
            { count: f.num, color: '#ef4444', label: f.num+'/'+f.den },
            { count: f.den - f.num, color: '#374151', label: '剩 '+(f.den-f.num)+'/'+f.den }
          ]);
        }
      } else if (family === 'percent'){
        var pVal2 = 0;
        var m2 = text.match(/(\d+)\s*[%％折]/);
        if (m2) pVal2 = parseInt(m2[1], 10);
        if (/折/.test(text)) pVal2 = pVal2 * 10;
        if (pVal2 > 0) html += '<div style="font-size:11px;color:#d29922">📊 '+pVal2+' 格塗色 / 100 格 = '+pVal2+'%</div>';
      }

      return html;
    }

    /* --- L4: 算式收斂 + 合理性檢查 --- */
    if (lv === 4){
      html += '<div class="he-rich-l4">' + escapeHTML(tpl.L4).replace(/\n/g, '<br>') + '</div>';

      /* Family-specific formula scaffolding */
      if (family === 'fracRemain' && fracs.length >= 2){
        var f1r = fracs[0], f2r = fracs[1];
        html += '<div class="he-formula">';
        html += '步驟① 1 − ' + f1r.num + '/' + f1r.den + ' = ' + (f1r.den-f1r.num) + '/' + f1r.den + ' (剩下)<br>';
        html += '步驟② ' + (f1r.den-f1r.num) + '/' + f1r.den + ' × ' + f2r.num + '/' + f2r.den + ' = ？（自行計算）<br>';
        html += '</div>';
        html += '<div class="he-check-ok">✅ 第二段 &lt; 剩下？全部 &gt; 答案？</div>';
        html += '<div class="he-check-bad">❌ 常見錯：直接用 1 × ' + f2r.num + '/' + f2r.den + '（忽略基準切換）</div>';
      } else if (family === 'percent'){
        var m3 = text.match(/(\d+)\s*[%％]/); var m3f = text.match(/(\d+)\s*折/);
        if (m3){
          html += '<div class="he-formula">列式：原量 × ' + m3[1] + '/100 = ？</div>';
        } else if (m3f){
          html += '<div class="he-formula">列式：原量 × ' + m3f[1] + '/10 = ？（' + m3f[1] + '折 = 0.' + m3f[1] + '）</div>';
        }
        html += '<div class="he-check-ok">✅ 打折 → 結果 &lt; 原價；加成 → 結果 &gt; 原量</div>';
      } else if (family === 'decimal'){
        html += '<div class="he-formula">先當整數算 → 再放回小數點（位數加總）</div>';
        html += '<div class="he-check-ok">✅ 用整數近似值檢查量級</div>';
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

    /* Replace exact answer occurrences */
    var hNorm = normalizeForCompare(h);
    if (hNorm.indexOf(ans) !== -1){
      /* Replace in the original (non-normalized) text */
      h = h.replace(new RegExp(escapeRegex(String(answer || '').trim()), 'g'), '（先自己算）');
    }

    /* Also catch patterns like "答案是 X", "= X (最終)" */
    h = h.replace(/(?:答案[是為]?|所以|因此|得到|等於)\s*[:：]?\s*\d[\d.\/\s]*(?:\s*[a-zA-Z%㎡³元個頁公分公尺]*)?\s*[。.！!]?/g, '（請自行完成最後計算）');
    h = h.replace(/=\s*\d[\d.\/\s]*\s*$/gm, '= ？（自行計算）');

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

        /* Wrong-answer diagnosis */
        if (isBad){
          var ansInput = document.getElementById('answer') || document.getElementById('ans') || document.getElementById('gAnswer');
          var wrongAns = ansInput ? ansInput.value : '';
          var diagnosis = diagnoseWrongAnswer(q, wrongAns);
          if (diagnosis && diagnosis.length > 0){
            showDiagnosisUI(diagnosis);
          }
        }
      }, 200); /* Wait for page's own check handler to set banner */
    }, true); /* Capture phase to run after native handler */
  }

  function showDiagnosisUI(diagList){
    /* Remove previous diagnosis */
    var old = document.getElementById('heDiagnosis');
    if (old) old.remove();

    var container = document.getElementById('hints') || document.getElementById('banner');
    if (!container || !container.parentElement) return;

    var wrap = document.createElement('div');
    wrap.id = 'heDiagnosis';
    wrap.className = 'he-diag';
    var title = document.createElement('div');
    title.className = 'he-diag-tag';
    title.textContent = '🔎 錯因診斷';
    wrap.appendChild(title);

    for (var i = 0; i < Math.min(diagList.length, 3); i++){
      var d = diagList[i];
      var item = document.createElement('div');
      item.className = 'he-diag-remedy';
      item.textContent = '• ' + d.remedy;
      wrap.appendChild(item);
    }

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
      '.he-diag{margin-top:8px;border:1px solid rgba(248,81,73,.35);border-radius:8px;padding:8px;background:rgba(248,81,73,.06)}',
      '.he-diag-tag{font-weight:800;color:#ffd2cf}',
      '.he-diag-remedy{margin-top:4px;color:#c9d1d9;font-size:13px}',
      /* Report */
      '.he-report{margin-top:10px;font-size:12px;border:1px solid rgba(88,166,255,.25);border-radius:8px;padding:8px;background:rgba(88,166,255,.05)}',
      /* Rich hint levels */
      '.he-rich-l1{color:#58a6ff;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l2{color:#3fb950;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l3{color:#d29922;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-l4{color:#f85149;font-weight:600;line-height:1.6;margin:4px 0}',
      '.he-rich-viz{margin:6px 0}',
      /* Formula scaffolding */
      '.he-formula{background:rgba(210,153,34,.1);border:1px solid rgba(210,153,34,.3);border-radius:6px;padding:6px 10px;margin:6px 0;font-family:monospace;font-size:13px;color:#e5e7eb;line-height:1.7}',
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

    /* Utilities */
    extractFractions: extractFractions,
    extractIntegers: extractIntegers,

    /* Page integration */
    setCurrentQuestion: setCurrentQuestion
  };

})();
