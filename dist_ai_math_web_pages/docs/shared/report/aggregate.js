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
    aggregate,
  };
})();
