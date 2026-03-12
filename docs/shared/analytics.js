/**
 * AIMathAnalytics — 最小可用的產品事件追蹤
 *
 * 儲存 key: aimath_analytics_v1
 * 所有事件記錄到 localStorage，可匯出 JSON。
 * 未來可替換為正式 analytics backend。
 */
(function(){
  'use strict';
  var KEY = 'aimath_analytics_v1';
  var MAX_EVENTS = 10000;
  var SESSION_KEY = 'aimath_session_id';
  var BUSINESS_EVENTS = {
    pricing_view: 1,
    trial_start: 1,
    upgrade_click: 1,
    report_open: 1,
    weekly_report_copy: 1,
    redeem_success: 1,
    redeem_fail: 1,
    paid_active: 1,
    expired: 1,
    task_center_open: 1
  };
  var BUSINESS_EVENT_ALIASES = {
    weekly_report_view: 'report_open',
    checkout_success: 'paid_active',
    subscription_expired: 'expired',
    subscription_force_expire: 'expired'
  };

  function getSessionId(){
    var sid = sessionStorage.getItem(SESSION_KEY);
    if (!sid){
      sid = 's_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6);
      sessionStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  function getUserId(){
    if (window.AIMathStudentAuth && window.AIMathStudentAuth.isLoggedIn()){
      var s = window.AIMathStudentAuth.getCurrentStudent();
      return s ? s.name : 'anonymous';
    }
    return 'anonymous';
  }

  function getRole(){
    // 從當前頁面推斷角色
    if (location.pathname.indexOf('parent-report') >= 0) return 'parent';
    if (location.pathname.indexOf('coach') >= 0) return 'coach';
    return 'student';
  }

  function loadEvents(){
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return [];
      return JSON.parse(raw);
    } catch(e){ return []; }
  }

  function saveEvents(events){
    // 保留最新 MAX_EVENTS 筆
    if (events.length > MAX_EVENTS){
      events = events.slice(events.length - MAX_EVENTS);
    }
    try { localStorage.setItem(KEY, JSON.stringify(events)); } catch(e){}
  }

  function normalizedEventName(name){
    var raw = String(name || '').trim();
    return BUSINESS_EVENT_ALIASES[raw] || raw;
  }

  function safeRate(num, den){
    var n = Number(num || 0);
    var d = Number(den || 0);
    if (!d) return null;
    return Math.round((n / d) * 1000) / 1000;
  }

  function summarizeBusinessEvents(events, lookbackMs){
    var list = Array.isArray(events) ? events.slice() : [];
    var now = Date.now();
    if (Number.isFinite(Number(lookbackMs)) && Number(lookbackMs) > 0){
      var cutoff = now - Number(lookbackMs);
      list = list.filter(function(e){ return Number(e && e.ts || 0) >= cutoff; });
    }

    var counts = {};
    Object.keys(BUSINESS_EVENTS).forEach(function(name){ counts[name] = 0; });
    var highIntentPages = {};
    var activeUsers = {};
    var returnUsers = {};

    list.forEach(function(e){
      var name = normalizedEventName(e && e.event);
      if (BUSINESS_EVENTS[name]) {
        counts[name] = (counts[name] || 0) + 1;
      }
      if (name === 'return_next_week' && e && e.user_id) {
        returnUsers[e.user_id] = 1;
      }
      if (/question_|task_center_open|report_open|pricing_view|trial_start|upgrade_click|redeem_success/.test(name) && e && e.user_id) {
        activeUsers[e.user_id] = 1;
      }
      if (BUSINESS_EVENTS[name]) {
        var pageKey = String((e && e.page) || ((e && e.data && e.data.page) || 'unknown'));
        highIntentPages[pageKey] = (highIntentPages[pageKey] || 0) + 1;
      }
    });

    var friction = [];
    if (counts.redeem_fail > 0) {
      friction.push({ id: 'redeem_fail', count: counts.redeem_fail, reason: '兌換失敗會直接中斷成交。' });
    }
    if (counts.upgrade_click > counts.trial_start) {
      friction.push({ id: 'upgrade_drop_after_click', count: counts.upgrade_click - counts.trial_start, reason: '升級點擊後沒有成功進入試用。' });
    }
    if (counts.expired > counts.paid_active) {
      friction.push({ id: 'expired_without_recovery', count: counts.expired, reason: '到期事件高於啟用事件，續費/回流需要加強。' });
    }

    var sortedPages = Object.keys(highIntentPages).map(function(page){
      return { page: page, count: highIntentPages[page] };
    }).sort(function(a, b){ return b.count - a.count; }).slice(0, 3);

    var activeCount = Object.keys(activeUsers).length;
    var retentionProxy = activeCount ? Math.round((Object.keys(returnUsers).length / activeCount) * 1000) / 1000 : null;
    var upgradeClickRate = safeRate(counts.upgrade_click, counts.pricing_view);
    var trialStartRate = safeRate(counts.trial_start, counts.upgrade_click);
    var reportOpenRate = safeRate(counts.report_open, activeCount);
    var redeemSuccessRate = safeRate(counts.redeem_success, counts.redeem_success + counts.redeem_fail);
    var health = 'insufficient_data';
    if (counts.pricing_view || counts.report_open || counts.task_center_open) {
      health = 'watch';
      if ((upgradeClickRate == null || upgradeClickRate >= 0.15) && (trialStartRate == null || trialStartRate >= 0.35) && (redeemSuccessRate == null || redeemSuccessRate >= 0.6)) {
        health = 'strong';
      } else if ((upgradeClickRate != null && upgradeClickRate < 0.05) || (trialStartRate != null && trialStartRate < 0.15) || (redeemSuccessRate != null && redeemSuccessRate < 0.3)) {
        health = 'improve';
      }
    }

    return {
      window_days: Number.isFinite(Number(lookbackMs)) && Number(lookbackMs) > 0 ? Math.round(Number(lookbackMs) / 86400000) : null,
      insufficient_data: health === 'insufficient_data',
      counts: counts,
      trial_start_rate: trialStartRate,
      upgrade_click_rate: upgradeClickRate,
      report_open_rate: reportOpenRate,
      redeem_success_rate: redeemSuccessRate,
      weekly_active_students: activeCount,
      retention_7d_proxy: retentionProxy,
      top_high_intent_pages: sortedPages,
      top_friction_points: friction.slice(0, 3),
      health: health
    };
  }

  /**
   * 記錄事件
   * @param {string} name - 事件名稱
   * @param {object} data - 附加資料
   */
  function track(name, data){
    var events = loadEvents();
    var d = data || {};
    // Auto-enrich: plan_status, module_id
    if (!d.plan_status) {
      try {
        if (window.AIMathSubscription && typeof window.AIMathSubscription.getPlanStatus === 'function') {
          d.plan_status = window.AIMathSubscription.getPlanStatus();
        }
      } catch(e){}
    }
    if (!d.module_id) {
      var parts = location.pathname.replace(/\/+$/, '').split('/');
      var last = parts[parts.length - 1];
      if (last && last !== 'docs' && last !== '') d.module_id = last;
    }
    var event = {
      event: name,
      ts: Date.now(),
      user_id: getUserId(),
      role: getRole(),
      session_id: getSessionId(),
      page: location.pathname,
      data: d
    };
    events.push(event);
    saveEvents(events);
  }

  /**
   * 查詢事件
   * @param {object} opts - { event, user_id, sinceMs, limit }
   */
  function query(opts){
    opts = opts || {};
    var events = loadEvents();
    if (opts.event){
      events = events.filter(function(e){ return e.event === opts.event; });
    }
    if (opts.user_id){
      events = events.filter(function(e){ return e.user_id === opts.user_id; });
    }
    if (opts.sinceMs){
      var cutoff = Date.now() - opts.sinceMs;
      events = events.filter(function(e){ return e.ts >= cutoff; });
    }
    if (opts.limit){
      events = events.slice(-opts.limit);
    }
    return events;
  }

  /**
   * 計算 KPI
   */
  function computeKPIs(){
    var all = loadEvents();
    var now = Date.now();
    var d7 = now - 7 * 86400000;
    var d30 = now - 30 * 86400000;
    var recent7 = all.filter(function(e){ return e.ts >= d7; });
    var recent30 = all.filter(function(e){ return e.ts >= d30; });

    function countEvent(list, name){
      return list.filter(function(e){ return e.event === name; }).length;
    }

    function uniqueUsers(list){
      var set = {};
      list.forEach(function(e){ if(e.user_id) set[e.user_id]=1; });
      return Object.keys(set).length;
    }

    // Topic breakdown: accuracy per topic_id (7d)
    var topicStats = {};
    recent7.forEach(function(e){
      if (e.event === 'question_submit' || e.event === 'question_correct'){
        var tid = (e.data && e.data.topic_id) || 'unknown';
        if (!topicStats[tid]) topicStats[tid] = { submit: 0, correct: 0 };
        topicStats[tid].submit++;
        if (e.event === 'question_correct') topicStats[tid].correct++;
      }
    });

    // CTA source breakdown (30d)
    var ctaSources = {};
    recent30.forEach(function(e){
      if (e.event === 'upgrade_click' && e.data && e.data.cta_source){
        var src = e.data.cta_source;
        ctaSources[src] = (ctaSources[src] || 0) + 1;
      }
    });

    return {
      total_events: all.length,
      events_7d: recent7.length,
      events_30d: recent30.length,
      unique_users_7d: uniqueUsers(recent7),
      unique_users_30d: uniqueUsers(recent30),
      trial_starts: countEvent(all, 'trial_start'),
      checkout_starts: countEvent(all, 'checkout_start'),
      checkout_success: countEvent(all, 'checkout_success'),
      pricing_views: countEvent(all, 'pricing_view'),
      upgrade_clicks: countEvent(all, 'upgrade_click'),
      question_submits_7d: countEvent(recent7, 'question_submit'),
      question_correct_7d: countEvent(recent7, 'question_correct'),
      question_starts_7d: countEvent(recent7, 'question_start'),
      hint_opens_7d: countEvent(recent7, 'hint_open'),
      report_views_7d: countEvent(recent7, 'weekly_report_view'),
      landing_views_7d: countEvent(recent7, 'landing_page_view'),
      return_next_day_30d: countEvent(recent30, 'return_next_day'),
      return_next_week_30d: countEvent(recent30, 'return_next_week'),
      session_completes_7d: countEvent(recent7, 'session_complete'),
      remedial_clicks_30d: countEvent(recent30, 'remedial_recommendation_click'),
      topic_accuracy_7d: topicStats,
      cta_source_breakdown_30d: ctaSources,
      business_daily: summarizeBusinessEvents(all, 86400000),
      business_7d: summarizeBusinessEvents(all, 7 * 86400000)
    };
  }

  /**
   * 匯出全部事件 JSON
   */
  function exportJSON(){
    return JSON.stringify(loadEvents(), null, 2);
  }

  function exportBusinessSummary(){
    return JSON.stringify({
      daily: summarizeBusinessEvents(loadEvents(), 86400000),
      d7: summarizeBusinessEvents(loadEvents(), 7 * 86400000)
    }, null, 2);
  }

  function clearAll(){
    try { localStorage.removeItem(KEY); } catch(e){}
  }

  // ─── Retention detection (return_next_day / return_next_week) ───
  var LAST_VISIT_KEY = 'aimath_last_visit';
  (function detectRetention(){
    try {
      var now = Date.now();
      var last = parseInt(localStorage.getItem(LAST_VISIT_KEY), 10);
      if (last){
        var gap = now - last;
        var DAY = 86400000;
        if (gap >= DAY && gap < 2 * DAY){
          track('return_next_day', { gap_hours: Math.round(gap / 3600000) });
        }
        if (gap >= 7 * DAY && gap < 8 * DAY){
          track('return_next_week', { gap_days: Math.round(gap / DAY) });
        }
      }
      localStorage.setItem(LAST_VISIT_KEY, String(now));
    } catch(e){}
  })();

  // ─── Session complete on page unload ───
  var sessionStart = Date.now();
  window.addEventListener('beforeunload', function(){
    var duration = Math.round((Date.now() - sessionStart) / 1000);
    if (duration > 2){ // ignore accidental loads
      track('session_complete', { duration_sec: duration, page: location.pathname });
    }
  });

  window.AIMathAnalytics = {
    track: track,
    query: query,
    computeKPIs: computeKPIs,
    computeBusinessSummary: summarizeBusinessEvents,
    exportJSON: exportJSON,
    exportBusinessSummary: exportBusinessSummary,
    normalizedEventName: normalizedEventName,
    clearAll: clearAll,
    getSessionId: getSessionId
  };
})();
