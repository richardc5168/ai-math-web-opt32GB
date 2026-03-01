const fs = require('fs');
const path = require('path');

function readJsonl(filePath) {
  return fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function writeJsonl(filePath, rows) {
  const content = rows.map((row) => JSON.stringify(row)).join('\n') + '\n';
  fs.writeFileSync(filePath, content, 'utf8');
}

function scoreBreakdown(item) {
  const breakdown = item.breakdown || {};
  return {
    strategy: Number(breakdown.strategy || 0),
    equation: Number(breakdown.equation || 0),
    compute: Number(breakdown.compute || 0),
    misconception: Number(breakdown.misconception || 0),
    check: Number(breakdown.check || 0),
  };
}

const cwd = process.cwd();
const goldenPath = path.join(cwd, 'golden', 'grade5_pack_v1.jsonl');
const judgePath = path.join(cwd, 'artifacts', 'hint_judge.json');
const reportPath = path.join(cwd, 'artifacts', 'autotune_report.json');
const policyPath = path.join(cwd, 'ops', 'hint_optimization_policy.json');

if (!fs.existsSync(goldenPath) || !fs.existsSync(judgePath)) {
  console.error('missing golden set or hint_judge artifact');
  process.exit(1);
}

const rows = readJsonl(goldenPath);
const judge = JSON.parse(fs.readFileSync(judgePath, 'utf8'));
const byId = new Map((judge.items || []).map((item) => [item.id, item]));

function readPolicy() {
  const defaults = {
    protected_templates: {
      match_any: ['國小五年級', '分數應用題', '離線練習', '三層提示'],
    },
    modes: {
      simple_one_step_keywords: ['打折', '折扣', '多少元', '平均', '單價', 'one-step'],
      multi_stage_drawing_keywords: ['線段圖', '畫圖', '分段', '路程', '多步驟', 'diagram', 'multi-step'],
      concise_max_chars: 34,
    },
  };
  if (!fs.existsSync(policyPath)) return defaults;
  try {
    const raw = JSON.parse(fs.readFileSync(policyPath, 'utf8'));
    return {
      protected_templates: {
        match_any: Array.isArray(raw?.protected_templates?.match_any)
          ? raw.protected_templates.match_any
          : defaults.protected_templates.match_any,
      },
      modes: {
        simple_one_step_keywords: Array.isArray(raw?.modes?.simple_one_step_keywords)
          ? raw.modes.simple_one_step_keywords
          : defaults.modes.simple_one_step_keywords,
        multi_stage_drawing_keywords: Array.isArray(raw?.modes?.multi_stage_drawing_keywords)
          ? raw.modes.multi_stage_drawing_keywords
          : defaults.modes.multi_stage_drawing_keywords,
        concise_max_chars: Number(raw?.modes?.concise_max_chars || defaults.modes.concise_max_chars),
      },
    };
  } catch {
    return defaults;
  }
}

function normalizeText(v) {
  return String(v || '').toLowerCase();
}

function matchesAny(text, keywords) {
  const lower = normalizeText(text);
  return (keywords || []).some((k) => lower.includes(normalizeText(k)));
}

function rowText(row) {
  return [
    row?.id,
    row?.topic,
    row?.prompt,
    ...(Array.isArray(row?.report_expectations?.skill_tags) ? row.report_expectations.skill_tags : []),
  ].join(' ');
}

function conciseHint(text, fallback, maxChars) {
  const source = String(text || '').trim();
  const first = source.split(/[。！？!?]/).map((s) => s.trim()).filter(Boolean)[0] || fallback;
  return first.length > maxChars ? `${first.slice(0, maxChars)}…` : first;
}

function detailedHint(text, addition) {
  const source = String(text || '').trim();
  if (!source) return addition;
  if (source.includes(addition)) return source;
  return `${source} ${addition}`;
}

const policy = readPolicy();

let changed = 0;
const touched = [];
const skippedProtected = [];
const modeStats = { simple: 0, multi: 0, normal: 0 };

for (const row of rows) {
  const judged = byId.get(row.id);
  if (!judged) continue;

  const text = rowText(row);
  if (matchesAny(text, policy.protected_templates.match_any)) {
    skippedProtected.push(row.id);
    continue;
  }

  const isMulti = matchesAny(text, policy.modes.multi_stage_drawing_keywords);
  const isSimple = !isMulti && matchesAny(text, policy.modes.simple_one_step_keywords);
  const mode = isMulti ? 'multi' : (isSimple ? 'simple' : 'normal');
  modeStats[mode] += 1;

  const b = scoreBreakdown(judged);

  const ladder = row.hint_ladder || {};
  let localChange = false;

  if (b.strategy < 2 && typeof ladder.h1_strategy === 'string') {
    if (mode === 'simple') {
      const next = conciseHint(ladder.h1_strategy, '先找關鍵數量，決定一步運算。', policy.modes.concise_max_chars);
      if (next !== ladder.h1_strategy) {
        ladder.h1_strategy = next;
        localChange = true;
      }
    } else if (mode === 'multi') {
      const next = detailedHint(ladder.h1_strategy, '先標出已知/未知，畫線段圖或表格，再拆成步驟。');
      if (next !== ladder.h1_strategy) {
        ladder.h1_strategy = next;
        localChange = true;
      }
    }
  }

  if (b.equation < 2 && typeof ladder.h2_equation === 'string' && !ladder.h2_equation.includes('列式：')) {
    if (mode === 'simple') {
      ladder.h2_equation = conciseHint(`列式：${ladder.h2_equation}`, '列式：先寫一個算式再算。', policy.modes.concise_max_chars);
    } else if (mode === 'multi') {
      ladder.h2_equation = detailedHint(`列式：${ladder.h2_equation}`, '每一步都先寫小算式，再串成總算式。');
    } else {
      ladder.h2_equation = `列式：${ladder.h2_equation}`;
    }
    localChange = true;
  }

  if (b.compute < 2 && typeof ladder.h3_compute === 'string') {
    if (mode === 'simple') {
      const next = conciseHint(ladder.h3_compute, '按算式一步算完，再寫答案。', policy.modes.concise_max_chars);
      if (next !== ladder.h3_compute) {
        ladder.h3_compute = next;
        localChange = true;
      }
    } else if (mode === 'multi') {
      const next = detailedHint(ladder.h3_compute, '逐步計算並保留中間結果，避免把前一步結果代錯。');
      if (next !== ladder.h3_compute) {
        ladder.h3_compute = next;
        localChange = true;
      }
    }
  }

  if (b.check < 2 && typeof ladder.h4_check_reflect === 'string') {
    if (mode === 'simple') {
      const next = conciseHint(ladder.h4_check_reflect, '最後用估算快速檢查合理性。', policy.modes.concise_max_chars);
      if (next !== ladder.h4_check_reflect) {
        ladder.h4_check_reflect = next;
        localChange = true;
      }
    } else if (mode === 'multi') {
      const next = detailedHint(ladder.h4_check_reflect, '回頭檢查每一步單位與題意是否一致，再做整體估算。');
      if (next !== ladder.h4_check_reflect) {
        ladder.h4_check_reflect = next;
        localChange = true;
      }
    }
  }

  if (b.check < 2 && mode === 'normal' && typeof ladder.h4_check_reflect === 'string' && !ladder.h4_check_reflect.includes('估算')) {
    ladder.h4_check_reflect = `${ladder.h4_check_reflect} 再用估算檢查量級是否合理。`;
    localChange = true;
  }

  if (b.misconception < 2) {
    const misconceptions = row.report_expectations?.misconceptions;
    if (Array.isArray(misconceptions) && misconceptions.length > 0) {
      const extra = '把提示內容誤當最終答案';
      if (!misconceptions.includes(extra)) {
        misconceptions.push(extra);
        localChange = true;
      }
    }
  }

  if (localChange) {
    row.hint_ladder = ladder;
    changed += 1;
    touched.push(row.id);
  }
}

if (changed > 0) {
  writeJsonl(goldenPath, rows);
}

fs.mkdirSync(path.join(cwd, 'artifacts'), { recursive: true });
fs.writeFileSync(
  reportPath,
  JSON.stringify(
    {
      changed,
      touched,
      skipped_protected_count: skippedProtected.length,
      skipped_protected_ids: skippedProtected.slice(0, 100),
      mode_stats: modeStats,
      source: 'rule-based-autotune',
      targetFile: 'golden/grade5_pack_v1.jsonl',
      policyFile: 'ops/hint_optimization_policy.json',
    },
    null,
    2
  ),
  'utf8'
);

console.log(`autotune complete, changed=${changed}, protected_skipped=${skippedProtected.length}`);
