/*
  AIMathReportAggregate (frontend)
  - Aggregates AttemptEvent[] into parent-readable stats.
  - Outputs in plain Chinese labels.
*/

(function(){
  'use strict';

  function toInt(x, d){
    const n = Number(x);
    return Number.isFinite(n) ? Math.trunc(n) : (d || 0);
  }

  function classifyQuadrant(evt){
    const isCorrect = !!evt?.is_correct;
    const shownLevels = Array.isArray(evt?.hint?.shown_levels) ? evt.hint.shown_levels : [];
    const shownSolution = !!evt?.steps?.shown_solution;
    const attemptsCount = Math.max(1, toInt(evt?.attempts_count, 1));

    const hasHint = shownLevels.length > 0 || shownSolution;

    // A: 無提示且一次就對
    if (isCorrect && !hasHint && attemptsCount === 1) return 'A';

    // B: 看提示後答對
    if (isCorrect && hasHint) return 'B';

    // C: 看提示仍答錯
    if (!isCorrect && hasHint) return 'C';

    // D: 無提示仍答錯
    return 'D';
  }

  function hintDepthKey(evt){
    const shownLevels = Array.isArray(evt?.hint?.shown_levels) ? evt.hint.shown_levels : [];
    const shownSolution = !!evt?.steps?.shown_solution;
    if (shownSolution) return 'solution';
    const maxLv = shownLevels.length ? Math.max.apply(null, shownLevels.map(x => Number(x) || 0)) : 0;
    if (maxLv >= 3) return 'L3';
    if (maxLv >= 2) return 'L2';
    if (maxLv >= 1) return 'L1';
    return 'none';
  }

  function emptyGroupStats(unitId, kind){
    return {
      unit_id: String(unitId || ''),
      kind: String(kind || 'unknown'),
      n: 0,
      correct: 0,
      independent_correct: 0,
      hint_correct: 0,
      hint_wrong: 0,
      nohint_wrong: 0,
      A: 0,
      B: 0,
      C: 0,
      D: 0,
      hint_level_hist: { none: 0, L1: 0, L2: 0, L3: 0, solution: 0 },
      first_try_correct: 0,
      avg_time_ms: 0,
    };
  }

  function emptyTopicStats(kind){
    return {
      kind: String(kind || 'unknown'),
      n: 0,
      correct: 0,
      independent_correct: 0,
      hint_correct: 0,
      hint_wrong: 0,
      nohint_wrong: 0,
      hint_level_hist: { none: 0, L1: 0, L2: 0, L3: 0, solution: 0 },
      first_try_correct: 0,
      avg_time_ms: 0,
    };
  }

  function aggregateByUnitKind(attempts){
    const items = Array.isArray(attempts) ? attempts : [];
    const byKey = {};

    for (const evt of items){
      const unitId = String(evt?.unit_id || '');
      const kind = String(evt?.kind || 'unknown');
      const key = unitId + '::' + kind;
      const st = byKey[key] || (byKey[key] = emptyGroupStats(unitId, kind));

      const q = classifyQuadrant(evt);
      const dkey = hintDepthKey(evt);

      const duration = Math.max(0, toInt(evt?.ts_end, 0) - toInt(evt?.ts_start, 0));
      const isCorrect = !!evt?.is_correct;
      const attemptsCount = Math.max(1, toInt(evt?.attempts_count, 1));

      st.n += 1;
      if (isCorrect) st.correct += 1;
      if (q === 'A') st.independent_correct += 1;
      if (q === 'B') st.hint_correct += 1;
      if (q === 'C') st.hint_wrong += 1;
      if (q === 'D') st.nohint_wrong += 1;
      st[q] = (st[q] || 0) + 1;
      st.hint_level_hist[dkey] = (st.hint_level_hist[dkey] || 0) + 1;
      if (isCorrect && attemptsCount === 1) st.first_try_correct += 1;
      st.avg_time_ms += duration;
    }

    const list = Object.values(byKey);
    for (const st of list){
      if (st.n) st.avg_time_ms = Math.round(st.avg_time_ms / st.n);
    }
    list.sort((a,b) => (b.n - a.n) || String(a.unit_id).localeCompare(String(b.unit_id)) || String(a.kind).localeCompare(String(b.kind)));
    return list;
  }

  function weaknessScore(row){
    const n = Math.max(0, toInt(row?.n, 0));
    if (!n) return 0;
    const cRate = (toInt(row?.C, 0) / n);
    const dRate = (toInt(row?.D, 0) / n);
    const bRate = (toInt(row?.B, 0) / n);
    // Heuristic: C is most urgent (hint still wrong), D next (no hint wrong), B indicates dependency.
    const base = 2.0 * cRate + 1.2 * dRate + 0.4 * bRate;
    // Weight by sample size but avoid overpowering.
    const w = Math.log(1 + n);
    return base * w;
  }

  function pickTopWeaknesses(unitKindRows, topN){
    const rows = Array.isArray(unitKindRows) ? unitKindRows : [];
    const n = Math.max(1, toInt(topN, 3));
    return rows
      .map(r => ({ ...r, weakness_score: weaknessScore(r) }))
      .filter(r => (r.n || 0) > 0)
      .sort((a,b) => (b.weakness_score - a.weakness_score) || ((b.n||0) - (a.n||0)))
      .slice(0, n);
  }

  function remedyLabel(row){
    const n = Math.max(0, toInt(row?.n, 0));
    if (!n) return { level: 'warn', title: '資料不足' };
    const cRate = (toInt(row?.C, 0) / n);
    const dRate = (toInt(row?.D, 0) / n);
    if (cRate >= 0.30) return { level: 'bad', title: '優先補救：看提示仍常錯' };
    if (dRate >= 0.30) return { level: 'warn', title: '需補強：不看提示就容易錯' };
    return { level: 'ok', title: '可加強：穩定度再提升' };
  }

  function aggregate(attempts){
    const items = Array.isArray(attempts) ? attempts : [];

    const overall = emptyTopicStats('overall');
    const byKind = {};

    for (const evt of items){
      const kind = String(evt?.kind || 'unknown');
      const st = byKind[kind] || (byKind[kind] = emptyTopicStats(kind));

      const q = classifyQuadrant(evt);
      const dkey = hintDepthKey(evt);

      const duration = Math.max(0, toInt(evt?.ts_end, 0) - toInt(evt?.ts_start, 0));
      const isCorrect = !!evt?.is_correct;
      const attemptsCount = Math.max(1, toInt(evt?.attempts_count, 1));

      function bump(target){
        target.n += 1;
        if (isCorrect) target.correct += 1;
        if (q === 'A') target.independent_correct += 1;
        if (q === 'B') target.hint_correct += 1;
        if (q === 'C') target.hint_wrong += 1;
        if (q === 'D') target.nohint_wrong += 1;
        target.hint_level_hist[dkey] = (target.hint_level_hist[dkey] || 0) + 1;
        if (isCorrect && attemptsCount === 1) target.first_try_correct += 1;
        target.avg_time_ms += duration;
      }

      bump(st);
      bump(overall);
    }

    function finalize(st){
      if (!st.n) return st;
      st.avg_time_ms = Math.round(st.avg_time_ms / st.n);
      return st;
    }

    finalize(overall);
    Object.values(byKind).forEach(finalize);

    const kindList = Object.values(byKind).sort((a,b) => b.n - a.n);

    const kpi = {
      total: overall.n,
      accuracy: overall.n ? overall.correct / overall.n : 0,
      independent_rate: overall.n ? overall.independent_correct / overall.n : 0,
      hint_dependency: overall.n ? (overall.hint_correct + overall.hint_wrong) / overall.n : 0,
      first_try_accuracy: overall.n ? overall.first_try_correct / overall.n : 0,
      avg_time_ms: overall.avg_time_ms,
    };

    return { overall, by_kind: kindList, kpi };
  }

  window.AIMathReportAggregate = {
    classifyQuadrant,
    hintDepthKey,
    aggregate,
    aggregateByUnitKind,
    pickTopWeaknesses,
    remedyLabel,
  };
})();
