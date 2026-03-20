(function(){
  'use strict';

  /* Delegate to shared topic_link_map.js (must be loaded first) */
  var _tlm = window.AIMathTopicLinkMap || {};
  var TOPIC_LINK_MAP = _tlm.TOPIC_LINK_MAP || {};

  function getTopicLink(topic){
    return (_tlm.getTopicLink || function(){ return '../star-pack/'; })(topic);
  }

  function toNumber(value, fallback){
    var number = Number(value);
    return Number.isFinite(number) ? number : (fallback || 0);
  }

  function getActiveDays(daily){
    return Object.keys(daily || {}).filter(function(key){
      return daily[key] && toNumber(daily[key].n, 0) > 0;
    }).length;
  }

  function addAction(actions, seen, action){
    if (!action) return;
    var uniqueKey = [action.concept, action.deep_link, action.action_text].join('|');
    if (seen[uniqueKey]) return;
    seen[uniqueKey] = true;
    actions.push(action);
  }

  function buildRecommendations(context){
    var report = context && (context.report || context) || {};
    var weak = Array.isArray(context && context.weak) ? context.weak : (Array.isArray(report.weak) ? report.weak : []);
    var daily = report.daily || {};
    var hintDist = Array.isArray(report.hintDist) ? report.hintDist : [0, 0, 0, 0];
    var stuckLevel = toNumber(context && context.stuckLevel, toNumber(report.stuckLevel, 0));
    var accuracy = toNumber(report.accuracy, 0);
    var activeDays = getActiveDays(daily);
    var actions = [];
    var seen = {};

    if (weak.length) {
      addAction(actions, seen, {
        priority: 1,
        concept: weak[0].t,
        reason: weak[0].reason || '錯題多且提示依賴高',
        action_text: '先補最常錯的題型，先做 5 到 10 題同類練習。',
        deep_link: getTopicLink(weak[0].t),
        evidence_tags: ['wrong_count_high', 'top_weakness', weak[0].k || '']
      });
    }

    if (stuckLevel >= 3) {
      addAction(actions, seen, {
        priority: actions.length + 1,
        concept: weak[0] ? weak[0].t : '基礎觀念',
        reason: '常需要完整提示才能解開，表示基礎步驟還不穩。',
        action_text: '先做基礎同類題，並把完整步驟寫一次再重做。',
        deep_link: getTopicLink(weak[0] ? weak[0].t : 'core'),
        evidence_tags: ['hint_l3_dependency', 'concept_rebuild']
      });
    } else if (stuckLevel >= 2 || toNumber(hintDist[2], 0) + toNumber(hintDist[3], 0) >= 2) {
      addAction(actions, seen, {
        priority: actions.length + 1,
        concept: weak[0] ? weak[0].t : '列式與拆題',
        reason: '看懂方向但列式不穩，容易在中間步驟卡住。',
        action_text: '先練題意轉算式，再做 3 題同結構題。',
        deep_link: getTopicLink(weak[0] ? weak[0].t : 'fraction-word'),
        evidence_tags: ['hint_l2_dependency', 'equation_setup']
      });
    }

    if (accuracy < 70) {
      addAction(actions, seen, {
        priority: actions.length + 1,
        concept: '正確率回穩',
        reason: '本週正確率偏低，先穩住正確率比追速度更重要。',
        action_text: '每天做 5 到 10 題基礎題，先把正確率拉回 70% 以上。',
        deep_link: '../interactive-g56-core-foundation/',
        evidence_tags: ['accuracy_low']
      });
    } else if (activeDays < 3) {
      addAction(actions, seen, {
        priority: actions.length + 1,
        concept: '學習節奏',
        reason: '練習天數偏少，週報代表性不夠穩定。',
        action_text: '先把節奏固定成連續 3 天短練習，再看進步趨勢。',
        deep_link: '../task-center/',
        evidence_tags: ['cadence_low']
      });
    }

    if (!actions.length) {
      addAction(actions, seen, {
        priority: 1,
        concept: '整體表現',
        reason: '目前整體狀態穩定，可以開始做整合型應用題。',
        action_text: '維持本週進度，進入明星題組做綜合練習。',
        deep_link: '../star-pack/',
        evidence_tags: ['stable_progress']
      });
    }

    return actions.slice(0, 3).map(function(action, index){
      return {
        priority: index + 1,
        concept: action.concept,
        reason: action.reason,
        action_text: action.action_text,
        deep_link: action.deep_link,
        evidence_tags: Array.isArray(action.evidence_tags) ? action.evidence_tags.filter(Boolean) : []
      };
    });
  }

  window.AIMathRecommendationEngine = {
    TOPIC_LINK_MAP: TOPIC_LINK_MAP,
    getTopicLink: getTopicLink,
    buildRecommendations: buildRecommendations
  };
})();
