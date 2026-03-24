(function(){
  'use strict';

  function toNumber(value, fallback){
    var number = Number(value);
    return Number.isFinite(number) ? number : (fallback || 0);
  }

  function parseAttemptTs(value){
    var asNumber = Number(value);
    if (Number.isFinite(asNumber) && asNumber > 0) return asNumber;
    var parsed = Date.parse(String(value || ''));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function getAttemptTs(attempt){
    if (!attempt) return 0;
    return parseAttemptTs(attempt.ts || attempt.ts_end || attempt.timestamp || attempt.answeredAt || attempt.submittedAt || attempt.createdAt);
  }

  function isAttemptCorrect(attempt){
    return !!(attempt && (attempt.ok || attempt.is_correct));
  }

  function getTimeMs(attempt){
    if (attempt && attempt.time_ms != null) return toNumber(attempt.time_ms, 0);
    if (attempt && attempt.time_spent_ms != null) return toNumber(attempt.time_spent_ms, 0);
    var start = toNumber(attempt && attempt.ts_start, 0);
    var end = toNumber(attempt && attempt.ts_end, 0);
    return start > 0 && end > start ? (end - start) : 0;
  }

  function getMaxHint(attempt){
    if (attempt && attempt.max_hint != null) return Math.max(0, Math.min(3, toNumber(attempt.max_hint, 0)));
    if (attempt && attempt.hint && Array.isArray(attempt.hint.shown_levels) && attempt.hint.shown_levels.length) {
      return Math.max.apply(null, attempt.hint.shown_levels.map(function(level){ return toNumber(level, 0); }));
    }
    if (attempt && attempt.hint && attempt.hint.shown_count != null) return Math.max(0, Math.min(3, toNumber(attempt.hint.shown_count, 0)));
    return 0;
  }

  function getTopic(attempt){
    return attempt && (attempt.unit_id || attempt.topic || attempt.topic_id) || '未分類';
  }

  function getModule(attempt){
    return attempt && (attempt.unit_id || attempt.module || attempt.moduleId || attempt.topic || attempt.topic_id) || '未分類';
  }

  function getKind(attempt){
    return attempt && (attempt.kind || attempt.template_id) || '';
  }

  function getQuestionText(attempt){
    if (attempt && attempt.question_text) return attempt.question_text;
    if (attempt && attempt.question) return attempt.question;
    if (attempt && attempt.extra && attempt.extra.question) return attempt.extra.question;
    return '';
  }

  function getAttemptKey(attempt){
    return [
      getAttemptTs(attempt),
      attempt && (attempt.question_id || attempt.qid || ''),
      getModule(attempt),
      getKind(attempt),
      isAttemptCorrect(attempt) ? 1 : 0,
      String(attempt && (attempt.student_answer_raw || attempt.student_answer || '') || '').slice(0, 40)
    ].join('|');
  }

  function dedupeAttempts(items){
    var seen = {};
    var list = [];
    (Array.isArray(items) ? items : []).forEach(function(item){
      var key = getAttemptKey(item);
      if (seen[key]) return;
      seen[key] = true;
      list.push(item);
    });
    list.sort(function(a, b){ return getAttemptTs(a) - getAttemptTs(b); });
    return list;
  }

  function normalizeAttemptForCloud(attempt){
    var ts = getAttemptTs(attempt);
    var extra = (attempt && attempt.extra && typeof attempt.extra === 'object') ? attempt.extra : {};
    var hint = (attempt && attempt.hint && typeof attempt.hint === 'object') ? attempt.hint : {};
    var out = {
      ts: ts,
      answeredAt: ts ? new Date(ts).toISOString() : '',
      ts_start: toNumber(attempt && attempt.ts_start, 0),
      ts_end: toNumber(attempt && attempt.ts_end, 0),
      question_id: String(attempt && (attempt.question_id || attempt.qid || '') || ''),
      ok: isAttemptCorrect(attempt),
      is_correct: isAttemptCorrect(attempt),
      time_ms: getTimeMs(attempt),
      max_hint: getMaxHint(attempt),
      unit_id: getModule(attempt),
      topic: getTopic(attempt),
      topic_id: String(attempt && attempt.topic_id || ''),
      kind: getKind(attempt),
      template_id: String(attempt && attempt.template_id || ''),
      question_text: String(getQuestionText(attempt) || '').slice(0, 200),
      student_answer_raw: String(attempt && (attempt.student_answer_raw || attempt.student_answer || '') || '').slice(0, 80),
      correct_answer: String(attempt && (attempt.correct_answer || attempt.answer || '') || '').slice(0, 80),
      error_type: String(attempt && attempt.error_type || ''),
      error_detail: String(attempt && attempt.error_detail || '').slice(0, 120)
    };
    /* R48: preserve hint evidence chain fields for cloud analytics */
    var hs = extra.hint_sequence || hint.hint_sequence;
    var ht = extra.hint_open_ts || hint.hint_open_ts;
    var hl = extra.hint_level_used != null ? extra.hint_level_used : hint.hint_level_used;
    if (Array.isArray(hs) && hs.length > 0) out.hint_sequence = hs;
    if (Array.isArray(ht) && ht.length > 0) out.hint_open_ts = ht;
    if (hl != null) out.hint_level_used = Number(hl);
    return out;
  }

  function buildWeakRows(attempts){
    var grouped = {};
    (Array.isArray(attempts) ? attempts : []).forEach(function(attempt){
      var topic = getTopic(attempt);
      var kind = getKind(attempt);
      var key = topic + '__' + kind;
      if (!grouped[key]) grouped[key] = { t: topic, k: kind, n: 0, w: 0, h2: 0, h3: 0 };
      grouped[key].n += 1;
      if (!isAttemptCorrect(attempt)) grouped[key].w += 1;
      if (getMaxHint(attempt) >= 2) grouped[key].h2 += 1;
      if (getMaxHint(attempt) >= 3) grouped[key].h3 += 1;
    });
    return Object.keys(grouped).map(function(key){ return grouped[key]; });
  }

  function getStuckLevel(hintDist){
    var dist = Array.isArray(hintDist) ? hintDist : [0, 0, 0, 0];
    var bestLevel = 0;
    var bestCount = 0;
    [1, 2, 3].forEach(function(level){
      var count = toNumber(dist[level], 0);
      if (count > bestCount) {
        bestCount = count;
        bestLevel = level;
      }
    });
    return bestLevel;
  }

  function buildPracticeSection(practiceEvents, nowMs){
    var list = Array.isArray(practiceEvents) ? practiceEvents.slice(-80) : [];
    var cutoff = nowMs - 7 * 86400000;
    var recent = list.filter(function(event){ return toNumber(event && event.ts, 0) >= cutoff; });
    var totalQuestions = recent.reduce(function(sum, event){ return sum + toNumber(event && event.total, 0); }, 0);
    var correctQuestions = recent.reduce(function(sum, event){ return sum + toNumber(event && event.score, 0); }, 0);
    var summary = {
      total_events: recent.length,
      total_questions: totalQuestions,
      correct_questions: correctQuestions,
      accuracy: totalQuestions ? Math.round(correctQuestions / totalQuestions * 100) : 0,
      latest: recent.length ? recent[recent.length - 1] : null
    };
    var byKind = {};
    recent.forEach(function(event){
      var key = String(event && (event.kind || event.topic) || '未分類');
      if (!byKind[key]) byKind[key] = { key: key, total: 0, score: 0, events: 0, acc: 0 };
      byKind[key].total += toNumber(event && event.total, 0);
      byKind[key].score += toNumber(event && event.score, 0);
      byKind[key].events += 1;
    });
    var rows = Object.keys(byKind).map(function(key){
      var row = byKind[key];
      row.acc = row.total ? Math.round(row.score / row.total * 100) : 0;
      return row;
    }).sort(function(a, b){ return b.total - a.total || b.acc - a.acc || a.key.localeCompare(b.key); });
    return { events: list, summary: summary, by_kind: rows };
  }

  function buildWeeklyFocus(report){
    var daily = report.daily || {};
    var activeDays = Object.keys(daily).filter(function(key){ return daily[key] && toNumber(daily[key].n, 0) > 0; }).length;
    var hintDist = Array.isArray(report.hintDist) ? report.hintDist : [0, 0, 0, 0];
    var hintRate = toNumber(report.total, 0) ? Math.round((toNumber(hintDist[1], 0) + toNumber(hintDist[2], 0) + toNumber(hintDist[3], 0)) / report.total * 100) : 0;
    var stuckLevel = getStuckLevel(hintDist);
    var weak = Array.isArray(report.weak) ? report.weak : [];
    var narrative = '本週資料還不夠，先累積 3 天以上練習，再看趨勢會更準。';
    var tone = 'muted';
    if (toNumber(report.total, 0) >= 5) {
      if (toNumber(report.accuracy, 0) >= 80 && hintRate < 35 && activeDays >= 3) {
        narrative = '這週狀態穩定：正確率高、提示依賴低，可以開始做更多整合應用題。';
        tone = 'ok';
      } else if (stuckLevel >= 2 || hintRate >= 45 || weak.length) {
        narrative = '這週最需要處理的是看懂題意後的列式與步驟，先做下方 3 個補救動作。';
        tone = 'warn';
      } else {
        narrative = '這週有基本進度，但仍有幾個觀念需要加強；先把最常錯的題型練穩。';
        tone = 'warn';
      }
    }
    return {
      items: [
        { label: '完成題數', value: String(report.total || 0), desc: '本週總作答量' },
        { label: '正確率', value: report.total ? String(report.accuracy) + '%' : '—', desc: '理解是否穩定' },
        { label: '主動完成天數', value: String(activeDays), desc: '有練習的天數' },
        { label: '提示使用比例', value: String(hintRate) + '%', desc: '是否過度依賴提示' }
      ],
      narrative: narrative,
      tone: tone,
      active_days: activeDays,
      hint_rate: hintRate
    };
  }

  function buildReportData(options){
    var nowMs = toNumber(options && options.nowMs, Date.now());
    var name = String(options && options.name || '未登入');
    var days = Math.max(1, toNumber(options && options.days, 7));
    var cutoff = nowMs - days * 86400000;
    var attempts = dedupeAttempts(Array.isArray(options && options.attempts) ? options.attempts : []).filter(function(attempt){
      return getAttemptTs(attempt) >= cutoff;
    });
    var total = attempts.length;
    var correct = attempts.filter(isAttemptCorrect).length;
    var totalMs = attempts.reduce(function(sum, attempt){ return sum + getTimeMs(attempt); }, 0);
    var hintDist = [0, 0, 0, 0];
    attempts.forEach(function(attempt){
      hintDist[Math.max(0, Math.min(3, getMaxHint(attempt)))] += 1;
    });
    var weakRows = buildWeakRows(attempts);
    var weaknessEngine = window.AIMathWeaknessEngine;
    var weak = weaknessEngine && weaknessEngine.rankWeaknessRows
      ? weaknessEngine.rankWeaknessRows(weakRows, 5)
      : weakRows;
    var wrong = attempts
      .filter(function(attempt){ return !isAttemptCorrect(attempt); })
      .sort(function(a, b){ return getAttemptTs(b) - getAttemptTs(a); })
      .slice(0, 5)
      .map(function(attempt){
        var ts = getAttemptTs(attempt);
        return {
          ts: ts,
          answeredAt: ts ? new Date(ts).toISOString() : '',
          q: String(getQuestionText(attempt) || '').slice(0, 60),
          sa: String(attempt && (attempt.student_answer_raw || attempt.student_answer || '') || '').slice(0, 20),
          ca: String(attempt && (attempt.correct_answer || attempt.answer || '') || '').slice(0, 20),
          t: getTopic(attempt),
          k: getKind(attempt),
          et: String(attempt && attempt.error_type || ''),
          ed: String(attempt && attempt.error_detail || '').slice(0, 60)
        };
      });

    var daily = {};
    attempts.forEach(function(attempt){
      var ts = getAttemptTs(attempt);
      var dateKey = ts ? new Date(ts).toISOString().slice(0, 10) : 'unknown';
      if (!daily[dateKey]) daily[dateKey] = { n: 0, ok: 0 };
      daily[dateKey].n += 1;
      if (isAttemptCorrect(attempt)) daily[dateKey].ok += 1;
    });

    var byModule = {};
    attempts.forEach(function(attempt){
      var moduleId = getModule(attempt);
      if (!byModule[moduleId]) byModule[moduleId] = { m: moduleId, n: 0, ok: 0, acc: 0 };
      byModule[moduleId].n += 1;
      if (isAttemptCorrect(attempt)) byModule[moduleId].ok += 1;
    });
    var modules = Object.keys(byModule).map(function(key){
      var row = byModule[key];
      row.acc = row.n ? Math.round(row.ok / row.n * 100) : 0;
      return row;
    }).sort(function(a, b){ return b.n - a.n || a.m.localeCompare(b.m); });

    var day24Cutoff = nowMs - 86400000;
    var last24 = attempts.filter(function(attempt){ return getAttemptTs(attempt) >= day24Cutoff; });
    var h24Modules = {};
    var h24Hint = [0, 0, 0, 0];
    last24.forEach(function(attempt){
      var moduleId = getModule(attempt);
      if (!h24Modules[moduleId]) h24Modules[moduleId] = { m: moduleId, n: 0, ok: 0, acc: 0 };
      h24Modules[moduleId].n += 1;
      if (isAttemptCorrect(attempt)) h24Modules[moduleId].ok += 1;
      h24Hint[Math.max(0, Math.min(3, getMaxHint(attempt)))] += 1;
    });
    var h24ModuleRows = Object.keys(h24Modules).map(function(key){
      var row = h24Modules[key];
      row.acc = row.n ? Math.round(row.ok / row.n * 100) : 0;
      return row;
    }).sort(function(a, b){ return b.n - a.n || a.m.localeCompare(b.m); });
    var practice = buildPracticeSection(options && options.practiceEvents, nowMs);

    var report = {
      v: 2,
      name: name,
      ts: nowMs,
      days: days,
      d: {
        total: total,
        correct: correct,
        incorrect: total - correct,
        accuracy: total ? Math.round(correct / total * 100) : 0,
        avgMs: total ? Math.round(totalMs / total) : 0,
        hintDist: hintDist,
        weak: weak,
        wrong: wrong,
        daily: daily,
        modules: modules,
        practice: practice,
        h24: {
          total: last24.length,
          correct: last24.filter(isAttemptCorrect).length,
          accuracy: last24.length ? Math.round(last24.filter(isAttemptCorrect).length / last24.length * 100) : 0,
          avgMs: last24.length ? Math.round(last24.reduce(function(sum, attempt){ return sum + getTimeMs(attempt); }, 0) / last24.length) : 0,
          hintDist: h24Hint,
          modules: h24ModuleRows
        }
      },
      _attempts: attempts.slice(-600)
    };
    report.d.stuckLevel = getStuckLevel(report.d.hintDist);
    report.d.weeklyFocus = buildWeeklyFocus(report.d);
    if (window.AIMathRecommendationEngine && window.AIMathRecommendationEngine.buildRecommendations) {
      report.d.recommendations = window.AIMathRecommendationEngine.buildRecommendations({ report: report.d, weak: report.d.weak, stuckLevel: report.d.stuckLevel });
    }
    return report;
  }

  function enrichReportData(report){
    if (!report || !report.d) return report;
    var clone = JSON.parse(JSON.stringify(report));
    clone.days = clone.days || 7;
    clone.d.practice = buildPracticeSection(clone.d.practice && clone.d.practice.events, toNumber(clone.ts, Date.now()));
    clone.d.stuckLevel = getStuckLevel(clone.d.hintDist);
    if (Array.isArray(clone.d.weak) && window.AIMathWeaknessEngine && window.AIMathWeaknessEngine.rankWeaknessRows) {
      clone.d.weak = window.AIMathWeaknessEngine.rankWeaknessRows(clone.d.weak, 5);
    }
    clone.d.weeklyFocus = buildWeeklyFocus(clone.d);
    if (window.AIMathRecommendationEngine && window.AIMathRecommendationEngine.buildRecommendations) {
      clone.d.recommendations = window.AIMathRecommendationEngine.buildRecommendations({ report: clone.d, weak: clone.d.weak, stuckLevel: clone.d.stuckLevel });
    }
    return clone;
  }

  window.AIMathReportDataBuilder = {
    parseAttemptTs: parseAttemptTs,
    getAttemptTs: getAttemptTs,
    isAttemptCorrect: isAttemptCorrect,
    getTimeMs: getTimeMs,
    getMaxHint: getMaxHint,
    getTopic: getTopic,
    getModule: getModule,
    getKind: getKind,
    getQuestionText: getQuestionText,
    getAttemptKey: getAttemptKey,
    dedupeAttempts: dedupeAttempts,
    normalizeAttemptForCloud: normalizeAttemptForCloud,
    getStuckLevel: getStuckLevel,
    buildPracticeSection: buildPracticeSection,
    buildWeeklyFocus: buildWeeklyFocus,
    buildReportData: buildReportData,
    enrichReportData: enrichReportData
  };
})();
