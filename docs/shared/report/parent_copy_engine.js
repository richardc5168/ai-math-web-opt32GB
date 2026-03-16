(function(){
  'use strict';

  function formatPracticeSummary(practice){
    if (!practice || !practice.summary || !practice.summary.total_events) return '最近 7 天尚無再練紀錄。';
    return '最近 7 天已再練 ' + practice.summary.total_events + ' 次，總題數 ' + practice.summary.total_questions + ' 題，正確率 ' + practice.summary.accuracy + '%。';
  }

  function buildParentCopy(input){
    var report = input && input.report || {};
    var studentName = String(input && input.studentName || input && input.name || '未知');
    var recommendations = Array.isArray(input && input.recommendations) ? input.recommendations : (Array.isArray(report.recommendations) ? report.recommendations : []);
    var weak = Array.isArray(report.weak) ? report.weak : [];
    var wrong = Array.isArray(report.wrong) ? report.wrong.slice(0, 3) : [];
    var lines = [];
    lines.push('【家長報告】' + studentName);
    lines.push('最近 ' + String(input && input.days || report.days || 7) + ' 天：共 ' + Number(report.total || 0) + ' 題，正確率 ' + Number(report.accuracy || 0) + '%。');

    if (weak.length) {
      lines.push('目前最需要補強：' + weak.slice(0, 3).map(function(item){ return item.t; }).join('、') + '。');
    }

    if (recommendations.length) {
      lines.push('接下來先做 3 件事：');
      recommendations.slice(0, 3).forEach(function(action, index){
        lines.push((index + 1) + '. ' + action.concept + '：' + action.action_text);
      });
    }

    lines.push(formatPracticeSummary(report.practice));

    if (wrong.length) {
      lines.push('最近錯題提醒：');
      wrong.forEach(function(item, index){
        lines.push((index + 1) + '. ' + item.t + '｜學生答 ' + item.sa + '，正解 ' + item.ca + '。');
      });
    }

    return lines.join('\n');
  }

  window.AIMathParentCopyEngine = {
    buildParentCopy: buildParentCopy
  };
})();
