#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { pythonCmd, runCommand, writeJson } = require('./_runner.cjs');

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function nowIso() {
  return new Date().toISOString();
}

function ensureDir(relPath) {
  const abs = path.join(process.cwd(), relPath);
  fs.mkdirSync(abs, { recursive: true });
  return abs;
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function parseLeadingJson(text, fallback) {
  if (!text || !text.trim()) return fallback;
  const trimmed = text.trim();
  const lastBrace = trimmed.lastIndexOf('}');
  if (lastBrace < 0) return fallback;
  try {
    return JSON.parse(trimmed.slice(0, lastBrace + 1));
  } catch (_) {
    return fallback;
  }
}

function appendJsonl(filePath, obj) {
  fs.appendFileSync(filePath, JSON.stringify(obj) + '\n', 'utf8');
}

function buildMarkdownSummary(summary) {
  const lines = [
    '# Solution Logic Reviewer Batch',
    '',
    `- generated_at: ${summary.generated_at}`,
    `- iteration: ${summary.iteration}`,
    `- avg_score: ${summary.avg_score}`,
    `- threshold: ${summary.threshold}`,
    `- below_threshold_count: ${summary.failed_count}`,
    `- hint_ladder_pass: ${summary.hint_ladder_pass}`,
    `- elementary_gate_pass: ${summary.elementary_gate_pass}`,
    `- verify_all_pass: ${summary.verify_all_pass}`,
    '',
    '## Top Issues',
  ];

  if (!summary.top_issues.length) {
    lines.push('- none');
  } else {
    summary.top_issues.forEach((item) => {
      lines.push(`- ${item.id}: ${item.issue_count} issues, avg_score=${item.avg_score}`);
    });
  }

  lines.push('', '## Commands', ...summary.commands.map((cmd) => `- ${cmd}`), '');
  return lines.join('\n');
}

function collectTopIssues(items) {
  return items
    .map((item) => ({
      id: item.id,
      avg_score: item.avg_score,
      issue_count: Array.isArray(item.issues) ? item.issues.length : 0,
    }))
    .filter((item) => item.issue_count > 0)
    .sort((a, b) => {
      if (a.avg_score !== b.avg_score) return a.avg_score - b.avg_score;
      return b.issue_count - a.issue_count;
    })
    .slice(0, 10);
}

async function main() {
  const py = pythonCmd();
  const HOURS = Number(argValue('--hours', '8'));
  const INTERVAL_MIN = Number(argValue('--interval-min', '60'));
  const PER_TEMPLATE = Number(argValue('--per-template', '5'));
  const SEED = Number(argValue('--seed', '12345'));
  const THRESHOLD = Number(argValue('--threshold', '3.5'));
  const ONCE = hasFlag('--once');
  const NO_VALIDATE = hasFlag('--no-validate');

  const artifactsDir = ensureDir('artifacts/reviewer_batch');
  const logJsonl = path.join(artifactsDir, 'reviewer_batch_runs.jsonl');
  const latestJson = path.join(artifactsDir, 'reviewer_batch_latest.json');
  const latestMd = path.join(artifactsDir, 'reviewer_batch_latest.md');

  const maxIterations = ONCE ? 1 : Math.max(1, Math.ceil((HOURS * 60) / INTERVAL_MIN));

  for (let iteration = 1; iteration <= maxIterations; iteration += 1) {
    console.log(`\n[reviewer-batch] iteration ${iteration}/${maxIterations}`);

    const dumpJsonl = path.join(artifactsDir, 'questions_dump_latest.jsonl');
    const dumpMd = path.join(artifactsDir, 'questions_dump_latest.md');
    const hintAuditJson = path.join(artifactsDir, 'hint_ladder_latest.json');
    const solutionAuditJson = path.join(artifactsDir, 'solution_logic_audit_latest.json');

    const commands = [
      `${py} scripts/export_all_questions.py --per_template ${PER_TEMPLATE} --seed ${SEED + iteration - 1} --out_jsonl ${dumpJsonl} --out_md ${dumpMd}`,
      `${py} scripts/validate_hint_ladder_rules.py --in_jsonl ${dumpJsonl}`,
      `node tools/reviewer_solution_logic.cjs --in_jsonl ${dumpJsonl} --out ${solutionAuditJson}`,
    ];

    const exportRes = runCommand(py, [
      'scripts/export_all_questions.py',
      '--per_template', String(PER_TEMPLATE),
      '--seed', String(SEED + iteration - 1),
      '--out_jsonl', dumpJsonl,
      '--out_md', dumpMd,
    ]);

    const hintRes = exportRes.pass
      ? runCommand(py, ['scripts/validate_hint_ladder_rules.py', '--in_jsonl', dumpJsonl])
      : { pass: false, stdout: '', stderr: 'export failed', status: 1 };

    const parsedHint = parseLeadingJson(hintRes.stdout, {
      total: 0,
      passed: 0,
      failed: 0,
      warnings: 0,
      failures: [],
    });
    fs.writeFileSync(hintAuditJson, JSON.stringify({
      ...parsedHint,
      status: hintRes.status,
      pass: hintRes.pass,
      stderr: hintRes.stderr || '',
    }, null, 2) + '\n', 'utf8');

    const reviewerRes = exportRes.pass
      ? runCommand('node', ['tools/reviewer_solution_logic.cjs', '--in_jsonl', dumpJsonl, '--out', solutionAuditJson])
      : { pass: false, stdout: '', stderr: 'export failed', status: 1 };

    let elementaryRes = { pass: true, status: 0 };
    let verifyAllRes = { pass: true, status: 0 };
    if (!NO_VALIDATE && reviewerRes.pass) {
      commands.push(`${py} tools/validate_all_elementary_banks.py`);
      commands.push(`${py} scripts/verify_all.py`);
      elementaryRes = runCommand(py, ['tools/validate_all_elementary_banks.py'], { timeout: 120000 });
      verifyAllRes = elementaryRes.pass
        ? runCommand(py, ['scripts/verify_all.py'], { timeout: 120000 })
        : { pass: false, status: 1 };
    }

    const solutionAudit = readJson(solutionAuditJson, { items: [], avg_score: 0, failed_count: 0 });
    const items = Array.isArray(solutionAudit.items) ? solutionAudit.items : [];
    const summary = {
      generated_at: nowIso(),
      iteration,
      hours: HOURS,
      interval_min: INTERVAL_MIN,
      per_template: PER_TEMPLATE,
      threshold: THRESHOLD,
      export_pass: !!exportRes.pass,
      hint_ladder_pass: !!hintRes.pass,
      reviewer_pass: !!reviewerRes.pass,
      elementary_gate_pass: !!elementaryRes.pass,
      verify_all_pass: !!verifyAllRes.pass,
      avg_score: Number(solutionAudit.avg_score || 0),
      failed_count: Number(solutionAudit.failed_count || 0),
      top_issues: collectTopIssues(items),
      commands,
      statuses: {
        export: exportRes.status,
        hint_ladder: hintRes.status,
        reviewer: reviewerRes.status,
        elementary: elementaryRes.status,
        verify_all: verifyAllRes.status,
      },
    };

    writeJson('reviewer_batch/reviewer_batch_latest.json', summary);
    fs.writeFileSync(latestMd, buildMarkdownSummary(summary) + '\n', 'utf8');
    appendJsonl(logJsonl, summary);

    const pass = summary.export_pass && summary.hint_ladder_pass && summary.reviewer_pass && summary.avg_score >= THRESHOLD && summary.failed_count === 0 && summary.elementary_gate_pass && summary.verify_all_pass;
    console.log(JSON.stringify({
      iteration: summary.iteration,
      avg_score: summary.avg_score,
      failed_count: summary.failed_count,
      verify_all_pass: summary.verify_all_pass,
      pass,
    }, null, 2));

    if (ONCE) {
      process.exit(pass ? 0 : 1);
    }

    if (iteration < maxIterations) {
      await sleep(INTERVAL_MIN * 60 * 1000);
    }
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
