#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function readJsonl(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  return raw
    .split(/\r?\n/)
    .map(function(line) { return line.trim(); })
    .filter(Boolean)
    .map(function(line, index) {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error('Invalid JSONL at line ' + (index + 1) + ': ' + error.message);
      }
    });
}

function toArray(value) {
  if (Array.isArray(value)) {
    return value
      .map(function(entry) {
        if (typeof entry === 'string') return entry.trim();
        if (entry && typeof entry === 'object') {
          const text = entry.text || entry.content || entry.step || entry.label;
          if (typeof text === 'string') return text.trim();
        }
        return String(entry || '').trim();
      })
      .filter(Boolean);
  }
  if (typeof value === 'string' && value.trim()) return [value.trim()];
  return [];
}

function itemId(item) {
  const direct = item.id || item.qid || item.question_id;
  if (direct) return String(direct);
  const templateId = item.template_id || item.templateId || item.template_name || item.topic_id;
  const seed = item.seed || item.variant_seed;
  if (templateId && seed) return String(templateId) + ':' + String(seed);
  if (templateId) return String(templateId);
  return 'unknown';
}

function firstText(item, keys) {
  for (let i = 0; i < keys.length; i += 1) {
    const value = item[keys[i]];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
}

function topicOf(item) {
  return String(item.topic || item.topic_id || item.module_topic || '').toLowerCase();
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce(function(sum, value) { return sum + value; }, 0) / values.length;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function issue(severity, type, detail) {
  return { severity: severity, type: type, detail: detail };
}

function detectLogic(item) {
  const steps = toArray(item.solution_steps || item.steps || item.teacherSteps);
  const issues = [];
  let score = 5;
  if (steps.length === 0) {
    score = 2;
    issues.push(issue('high', 'missing_steps', '缺少可審查的解題步驟。'));
  }
  if (steps.length > 0 && steps.length < 2) {
    score -= 1.5;
    issues.push(issue('medium', 'logic_gap', '步驟過少，學生可能只能看到結論。'));
  }
  const longSteps = steps.filter(function(step) { return step.length > 90; });
  if (longSteps.length) {
    score -= 1;
    issues.push(issue('medium', 'logic_gap', '部分步驟過長，容易把多個推理塞在同一句。'));
  }
  const duplicateCount = new Set(steps.map(function(step) { return step.trim(); })).size !== steps.length;
  if (duplicateCount) {
    score -= 0.5;
    issues.push(issue('low', 'logic_repetition', '解題步驟有重複描述。'));
  }
  const missingConnectors = steps.length >= 2 && steps.every(function(step) {
    return !/(先|再|接著|最後|因此|所以)/.test(step);
  });
  if (missingConnectors) {
    score -= 0.5;
    issues.push(issue('low', 'logic_flow', '步驟間缺少連接語，閱讀順序不夠明確。'));
  }
  return { score: clamp(score, 0, 5), issues: issues };
}

function detectChildWording(item) {
  const texts = []
    .concat(toArray(item.hints))
    .concat(toArray(item.solution_steps || item.steps || item.teacherSteps))
    .concat(toArray(item.question));
  const joined = texts.join(' ');
  const issues = [];
  let score = 5;
  const jargonList = ['cohort', 'telemetry', 'variance', 'normalize', '轉換率優化', '抽象化', '推導式'];
  const hitJargon = jargonList.filter(function(word) { return joined.indexOf(word) >= 0; });
  if (hitJargon.length) {
    score -= 2;
    issues.push(issue('high', 'wording_too_complex', '出現偏技術或抽象詞：' + hitJargon.join('、')));
  }
  const avgLength = average(texts.map(function(text) { return text.length; }));
  if (avgLength > 55) {
    score -= 1.5;
    issues.push(issue('medium', 'sentence_too_long', '平均句長偏高，孩子閱讀負擔較大。'));
  }
  const denseTexts = texts.filter(function(text) { return /，.*，.*，/.test(text); });
  if (denseTexts.length) {
    score -= 0.5;
    issues.push(issue('low', 'dense_wording', '部分文字資訊密度偏高，可拆短句。'));
  }
  return { score: clamp(score, 0, 5), issues: issues };
}

function detectParentClarity(item) {
  const summary = firstText(item, ['parent_summary', 'parentSummary', 'report_summary', 'summary']);
  const issues = [];
  let score = 5;
  if (!summary) {
    score = 2;
    issues.push(issue('medium', 'parent_unclear', '缺少家長摘要，無法檢查家長端可讀性。'));
    return { score: score, issues: issues };
  }
  if (summary.length > 120) {
    score -= 1.5;
    issues.push(issue('medium', 'parent_too_long', '家長摘要偏長，不利於 30 秒內抓重點。'));
  }
  if (!/(先|建議|本週|下週|優先|需要)/.test(summary)) {
    score -= 1;
    issues.push(issue('medium', 'parent_no_action', '摘要有現況，但缺少清楚的下一步或優先順序。'));
  }
  if (/(cohort|telemetry|assignment|conversion|variant)/i.test(summary)) {
    score -= 2;
    issues.push(issue('high', 'parent_too_technical', '家長摘要混入產品分析術語。'));
  }
  return { score: clamp(score, 0, 5), issues: issues };
}

function detectChart(item) {
  const chart = item.chart_config || item.chartConfig || item.diagram || null;
  const topic = topicOf(item);
  const question = firstText(item, ['question', 'prompt', 'stem']).toLowerCase();
  const issues = [];
  let score = 5;
  const pureCalculation = /計算[:：]?/.test(question) || / = /.test(question);
  if (!chart) {
    if (pureCalculation) {
      return { score: 5, issues: issues };
    }
    score = 3;
    issues.push(issue('low', 'chart_missing', '沒有圖表；若屬文字應用題，可考慮加入適度視覺提示。'));
    return { score: score, issues: issues };
  }
  const chartType = String(chart.type || chart.kind || '').toLowerCase();
  const labels = chart.labels || chart.dims || chart.markers || [];
  const expected = [];
  if (topic.indexOf('fraction') >= 0) expected.push('fraction_bar', 'area_model', 'number_line');
  if (topic.indexOf('decimal') >= 0) expected.push('place_value', 'number_line', 'grid');
  if (topic.indexOf('percent') >= 0) expected.push('percent_strip', 'bar', 'pie', 'ratio_table');
  if (topic.indexOf('life') >= 0 || /單價|折扣|平均|時間|單位/.test(question)) expected.push('bar', 'strip', 'timeline', 'table');
  if (topic.indexOf('volume') >= 0 || /體積|長方體|正方體/.test(question)) expected.push('rect_prism', 'cube', 'net');
  if (expected.length && expected.indexOf(chartType) < 0) {
    score -= 2;
    issues.push(issue('high', 'chart_mismatch', '圖表型別 `' + chartType + '` 和題型不夠匹配。'));
  }
  if (!labels || labels.length === 0) {
    score -= 1;
    issues.push(issue('medium', 'chart_unlabeled', '圖表缺少標示，孩子難以對照題意。'));
  }
  return { score: clamp(score, 0, 5), issues: issues };
}

function auditItem(item) {
  const logic = detectLogic(item);
  const wording = detectChildWording(item);
  const parent = detectParentClarity(item);
  const chart = detectChart(item);
  const avgScore = Number(((logic.score + wording.score + parent.score + chart.score) / 4).toFixed(2));
  const issues = logic.issues.concat(wording.issues, parent.issues, chart.issues);
  const recommendations = [];
  if (logic.score < 4) recommendations.push('把解題步驟拆成更短、更明確的順序句。');
  if (wording.score < 4) recommendations.push('把提示改成孩子口語能直接理解的短句。');
  if (parent.score < 4) recommendations.push('家長摘要要直接指出現況、風險與下一步。');
  if (chart.score < 4) recommendations.push('檢查是否需要更貼近題型的圖表，並補齊標示。');
  return {
    id: itemId(item),
    solution_logic_clarity: logic.score,
    child_friendly_wording: wording.score,
    parent_report_usability: parent.score,
    chart_appropriateness: chart.score,
    avg_score: avgScore,
    issues: issues,
    recommendations: recommendations
  };
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.in_jsonl) {
    console.error('Usage: node tools/reviewer_solution_logic.cjs --in_jsonl <file> [--out <file>]');
    process.exit(1);
  }
  const inputPath = path.resolve(args.in_jsonl);
  const items = readJsonl(inputPath);
  const audits = items.map(auditItem);
  const belowThreshold = audits.filter(function(item) { return item.avg_score < 3.5; });
  const summary = {
    generated_at: new Date().toISOString(),
    input: inputPath,
    total_items: audits.length,
    avg_score: Number(average(audits.map(function(item) { return item.avg_score; })).toFixed(2)),
    failed_count: belowThreshold.length,
    threshold: 3.5,
    items: audits
  };
  if (args.out) {
    const outPath = path.resolve(args.out);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, JSON.stringify(summary, null, 2) + '\n', 'utf8');
  }
  console.log(JSON.stringify({
    total_items: summary.total_items,
    avg_score: summary.avg_score,
    failed_count: summary.failed_count,
    threshold: summary.threshold
  }, null, 2));
}

main();
