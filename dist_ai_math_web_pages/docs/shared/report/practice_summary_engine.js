/*  practice_summary_engine.js  –  AIMathPracticeSummaryEngine
 *  Pure-function aggregation of re-practice events for parent-report.
 *  Browser IIFE – exposes window.AIMathPracticeSummaryEngine
 */
(function(){
  'use strict';

  /**
   * Filter events to the recent N-day window.
   * @param {Array} events  – raw practice event objects (each has .ts)
   * @param {number} [days=7] – window size in days
   * @param {number} [nowMs]  – override Date.now() for testing
   * @returns {Array} events whose ts >= (now - days*86400000)
   */
  function recentEvents(events, days, nowMs) {
    if (!Array.isArray(events)) return [];
    var d = (typeof days === 'number' && days > 0) ? days : 7;
    var now = (typeof nowMs === 'number') ? nowMs : Date.now();
    var since = now - d * 86400000;
    return events.filter(function(e) {
      return e && Number(e.ts || 0) >= since;
    });
  }

  /**
   * Aggregate practice stats from a list of events.
   * @param {Array} events – already-filtered events (each has .total, .score, .ts, .topic, .kind)
   * @returns {{ totalQ:number, correctQ:number, acc:number, count:number, latestText:string }}
   */
  function aggregateStats(events) {
    if (!events || !events.length) {
      return { totalQ: 0, correctQ: 0, acc: 0, count: 0, latestText: '' };
    }
    var totalQ = 0, correctQ = 0;
    for (var i = 0; i < events.length; i++) {
      totalQ += Number(events[i].total || 0);
      correctQ += Number(events[i].score || 0);
    }
    var acc = totalQ ? Math.round(correctQ / totalQ * 100) : 0;
    var latest = events[events.length - 1];
    var latestText = '';
    if (latest && latest.ts) {
      try {
        latestText = new Date(latest.ts).toLocaleString('zh-TW') +
          '｜' + (latest.topic || '未分類') + ' / ' + (latest.kind || '練習');
      } catch (e) {
        latestText = '—';
      }
    }
    return { totalQ: totalQ, correctQ: correctQ, acc: acc, count: events.length, latestText: latestText };
  }

  /**
   * Group events by kind (or topic), returning sorted rows.
   * @param {Array} events – already-filtered events
   * @returns {Array<{k:string, total:number, score:number, n:number, acc:number}>}
   */
  function groupByKind(events) {
    if (!events || !events.length) return [];
    var byKind = {};
    for (var i = 0; i < events.length; i++) {
      var e = events[i];
      var key = String(e.kind || e.topic || '未分類').trim() || '未分類';
      if (!byKind[key]) byKind[key] = { total: 0, score: 0, n: 0 };
      byKind[key].total += Number(e.total || 0);
      byKind[key].score += Number(e.score || 0);
      byKind[key].n += 1;
    }
    return Object.keys(byKind).map(function(k) {
      var v = byKind[k];
      var a = v.total ? Math.round(v.score / v.total * 100) : 0;
      return { k: k, total: v.total, score: v.score, n: v.n, acc: a };
    }).sort(function(a, b) {
      return b.total - a.total || b.acc - a.acc;
    });
  }

  window.AIMathPracticeSummaryEngine = {
    recentEvents: recentEvents,
    aggregateStats: aggregateStats,
    groupByKind: groupByKind
  };
})();
