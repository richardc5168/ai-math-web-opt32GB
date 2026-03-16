(function(){
  'use strict';

  function toNumber(value, fallback){
    var number = Number(value);
    return Number.isFinite(number) ? number : (fallback || 0);
  }

  function weaknessScore(row){
    var wrong = Math.max(0, toNumber(row && row.w, 0));
    var hint2 = Math.max(0, toNumber(row && row.h2, 0));
    var hint3 = Math.max(0, toNumber(row && row.h3, 0));
    var attempts = Math.max(0, toNumber(row && row.n, 0));
    if (!attempts) return 0;
    return wrong + hint2 * 0.25 + hint3 * 0.25 + Math.min(1, attempts / 10);
  }

  function describeWeaknessReason(row){
    if (!row) return '資料不足';
    if (toNumber(row.w, 0) >= 3) return '近期連續答錯，代表這個概念還沒有穩定。';
    if (toNumber(row.h3, 0) >= 1) return '常需要完整提示才解得開，基礎步驟仍不穩。';
    if (toNumber(row.h2, 0) >= 2) return '看懂方向但列式或拆題仍容易卡住。';
    return '本週仍有零星錯題，需要用短練習把流程練熟。';
  }

  function nextActionText(row){
    if (!row) return '先回到同類型基礎題做短練習。';
    if (toNumber(row.h3, 0) >= 1) return '先做基礎同類題，邊做邊把步驟寫出來。';
    if (toNumber(row.h2, 0) >= 2) return '先練題意轉算式，再做 3 到 5 題同型題。';
    return '先重做最近錯題，再補 3 題同類型題。';
  }

  function rankWeaknessRows(rows, topN){
    var limit = Math.max(1, toNumber(topN, 5));
    return (Array.isArray(rows) ? rows : [])
      .map(function(row){
        return {
          t: String(row && row.t || ''),
          k: String(row && row.k || ''),
          w: Math.max(0, toNumber(row && row.w, 0)),
          n: Math.max(0, toNumber(row && row.n, 0)),
          h2: Math.max(0, toNumber(row && row.h2, 0)),
          h3: Math.max(0, toNumber(row && row.h3, 0)),
          score: weaknessScore(row),
          reason: describeWeaknessReason(row),
          next_action: nextActionText(row)
        };
      })
      .filter(function(row){ return row.w > 0; })
      .sort(function(a, b){
        return b.score - a.score || b.w - a.w || b.h3 - a.h3 || b.h2 - a.h2 || a.t.localeCompare(b.t) || a.k.localeCompare(b.k);
      })
      .slice(0, limit);
  }

  window.AIMathWeaknessEngine = {
    weaknessScore: weaknessScore,
    describeWeaknessReason: describeWeaknessReason,
    nextActionText: nextActionText,
    rankWeaknessRows: rankWeaknessRows
  };
})();
