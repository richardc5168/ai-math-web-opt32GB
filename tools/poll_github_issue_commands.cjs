/*
  GitHub Issue Command Poller (Scheme B)

  Purpose:
  - Allow issuing commands to the local AI agent via GitHub Issues/Comments.
  - Provide progress/status back as Issue comments.
  - Enforce a strict allow-list (no arbitrary shell execution).

  Requires:
  - GitHub CLI: gh
  - Auth: gh auth login

  Command format (issue body or comment):
  ```agent
  {"id":"cmd-2026-03-04-001","task":"validate_all","note":"optional"}
  ```
*/

const fs = require('fs');
const path = require('path');
const { runCommand, pythonCmd } = require('./_runner.cjs');

const STATE_PATH_DEFAULT = path.join(process.cwd(), 'artifacts', 'issue_command_state.json');
const RUN_LOG_PATH_DEFAULT = path.join(process.cwd(), 'artifacts', 'issue_command_runs.jsonl');

const DEFAULT_REPO = 'richardc5168/ai-math-web';
const DEFAULT_LABEL = 'agent-command';

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

function ensureArtifacts() {
  fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
}

function readState(statePath) {
  if (!fs.existsSync(statePath)) return { executed_ids: [], last_checked_at: null };
  try {
    const obj = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    if (!obj || typeof obj !== 'object') return { executed_ids: [], last_checked_at: null };
    if (!Array.isArray(obj.executed_ids)) obj.executed_ids = [];
    return obj;
  } catch {
    return { executed_ids: [], last_checked_at: null };
  }
}

function writeState(statePath, state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
}

function appendRunLog(runLogPath, entry) {
  fs.mkdirSync(path.dirname(runLogPath), { recursive: true });
  fs.appendFileSync(runLogPath, `${JSON.stringify(entry)}\n`, 'utf8');
}

function nowIso() {
  return new Date().toISOString();
}

function truncateLog(s, max = 3800) {
  const t = String(s || '');
  if (t.length <= max) return t;
  return t.slice(0, max) + `\n...[truncated ${t.length - max} chars]`;
}

function parseJsonWithObjectFallback(content, sourceLabel) {
  const text = String(content || '').trim();
  try {
    return JSON.parse(text);
  } catch {
    const first = text.indexOf('{');
    if (first < 0) throw new Error(`invalid json in ${sourceLabel}: no object start`);
    let depth = 0;
    let end = -1;
    for (let i = first; i < text.length; i += 1) {
      const ch = text[i];
      if (ch === '{') depth += 1;
      if (ch === '}') {
        depth -= 1;
        if (depth === 0) {
          end = i;
          break;
        }
      }
    }
    if (end < 0) throw new Error(`invalid json in ${sourceLabel}: no balanced object end`);
    return JSON.parse(text.slice(first, end + 1));
  }
}

function extractAgentBlocks(markdownText) {
  const s = String(markdownText || '');
  const blocks = [];
  const re = /```agent\s*([\s\S]*?)```/g;
  for (;;) {
    const m = re.exec(s);
    if (!m) break;
    blocks.push(m[1]);
  }
  return blocks;
}

function normalizeCommand(obj, meta) {
  if (!obj || typeof obj !== 'object') return null;
  const id = String(obj.id || '').trim();
  const task = String(obj.task || '').trim();
  if (!id || !task) return null;
  return {
    id,
    task,
    note: obj.note ? String(obj.note) : '',
    args: obj.args && typeof obj.args === 'object' ? obj.args : null,
    close_issue: Boolean(obj.close_issue),
    source: meta,
  };
}

function allowList() {
  // Keep this allow-list intentionally small and stability-first.
  // Add new tasks ONLY if they are safe, idempotent, and non-destructive.
  return new Map([
    // --- Validation & Testing ---
    ['validate_all', { kind: 'py', argv: ['tools/validate_all_elementary_banks.py'], desc: '驗證所有題庫（4000+ 題）' }],
    ['verify_all', { kind: 'py', argv: ['scripts/verify_all.py'], desc: '完整驗證（docs/dist 同步 + endpoints + pytest）' }],
    ['cross_validate_remote', { kind: 'node', argv: ['tools/cross_validate_remote.cjs'], desc: '遠端交叉驗證（比對 local vs GitHub Pages）' }],
    ['pytest', { kind: 'py', argv: ['-m', 'pytest', '-q'], desc: '執行 pytest 測試' }],
    // --- npm 腳本 ---
    ['npm_judge_hints', { kind: 'npm', argv: ['run', 'judge:hints'], desc: '評分提示品質' }],
    ['npm_autotune_hints', { kind: 'npm', argv: ['run', 'autotune:hints'], desc: '自動調整提示' }],
    // --- 狀態查詢 (唯讀) ---
    ['status', { kind: 'builtin', desc: '回報 git status + 最近 commit + 驗證狀態' }],
    ['git_log', { kind: 'builtin', desc: '回報最近 10 筆 commit' }],
    ['list_tasks', { kind: 'builtin', desc: '列出所有可用命令' }],
    ['disk_usage', { kind: 'builtin', desc: '回報 docs/ 與 dist/ 的大小統計' }],
    ['freeform', { kind: 'builtin', desc: '自由文字命令（自動關鍵字比對）' }],
  ]);
}

// --- Freeform text → task matching ---
// Maps Chinese/English keywords in free-text to known tasks.
function matchTasksFromText(text) {
  const s = String(text || '').toLowerCase();
  const keywordMap = [
    { keywords: ['validate_all', '驗證', '題庫驗證', '驗證所有', '驗證題庫'], task: 'validate_all' },
    { keywords: ['verify_all', '完整驗證', '驗證同步', 'verify'], task: 'verify_all' },
    { keywords: ['cross_validate', '遠端驗證', '交叉驗證', 'remote'], task: 'cross_validate_remote' },
    { keywords: ['pytest', '測試', 'test', '單元測試'], task: 'pytest' },
    { keywords: ['judge_hints', '評分', '提示品質', 'hint quality'], task: 'npm_judge_hints' },
    { keywords: ['autotune', '自動調整', '調整提示'], task: 'npm_autotune_hints' },
    { keywords: ['status', '狀態', '回報', '目前狀態'], task: 'status' },
    { keywords: ['git_log', 'log', '紀錄', 'commit', '提交紀錄'], task: 'git_log' },
    { keywords: ['list_tasks', '可用命令', '命令列表', '有哪些命令'], task: 'list_tasks' },
    { keywords: ['disk_usage', '磁碟', '檔案數', '大小統計'], task: 'disk_usage' },
  ];
  const matched = [];
  for (const entry of keywordMap) {
    for (const kw of entry.keywords) {
      if (s.includes(kw.toLowerCase())) {
        if (!matched.includes(entry.task)) matched.push(entry.task);
        break;
      }
    }
  }
  return matched;
}

// Synthesize commands from an Issue that has no ```agent``` block.
// Auto-generates id from issue number, matches keywords to tasks.
function synthesizeFreeformCommands(issueObj) {
  const issueNumber = issueObj.number;
  const issueAuthor = toAuthorLogin(issueObj.author);
  const bodyText = String(issueObj.body || '') + ' ' + String(issueObj.title || '');
  const matched = matchTasksFromText(bodyText);

  if (matched.length > 0) {
    // Create one command per matched task – auto-close after last one
    return matched.map((task, idx) => ({
      id: `auto-issue${issueNumber}-${task}`,
      task,
      note: `(auto-matched from freeform Issue #${issueNumber})`,
      args: null,
      close_issue: idx === matched.length - 1,   // close on final task
      source: {
        issue_number: issueNumber,
        source: 'freeform_match',
        author: issueAuthor,
      },
    }));
  }

  // No keyword match → create a freeform acknowledgement command
  return [{
    id: `auto-issue${issueNumber}-freeform`,
    task: 'freeform',
    note: bodyText.slice(0, 500),
    args: { original_text: bodyText.slice(0, 2000) },
    close_issue: true,
    source: {
      issue_number: issueNumber,
      source: 'freeform_no_match',
      author: issueAuthor,
    },
  }];
}

function resolveGh() {
  // gh may not be on PATH; try known install locations first, then bare 'gh'.
  const fullPaths = [
    'C:\\Program Files\\GitHub CLI\\gh.exe',
    'C:\\Program Files (x86)\\GitHub CLI\\gh.exe',
  ];
  for (const p of fullPaths) {
    if (fs.existsSync(p)) return p;
  }
  return 'gh'; // fallback to bare command (may work if PATH is set)
}

const GH_CMD = resolveGh();

function runBuiltinTask(taskKey) {
  if (taskKey === 'list_tasks') {
    const tasks = allowList();
    const lines = ['可用命令一覽：', ''];
    for (const [k, v] of tasks) {
      lines.push(`- \`${k}\` — ${v.desc || '(no description)'}`);
    }
    lines.push('', '用法：在 Issue 中貼上：', '````agent', '{"id":"cmd-唯一ID","task":"命令名"}', '````');
    return { pass: true, status: 0, stdout: lines.join('\n'), stderr: '' };
  }

  if (taskKey === 'status') {
    const gitStatus = runCommand('git', ['status', '--short']);
    const gitLog = runCommand('git', ['-c', 'core.pager=cat', 'log', '--oneline', '-5']);
    const gitBranch = runCommand('git', ['branch', '-vv', '--no-color']);
    const lines = [
      '## Git Status',
      '```', gitStatus.stdout || '(clean)', '```',
      '',
      '## Recent Commits (last 5)',
      '```', gitLog.stdout || '(none)', '```',
      '',
      '## Branch Info',
      '```', gitBranch.stdout || '(unknown)', '```',
      '',
      `Reported at: ${nowIso()}`,
    ];
    return { pass: true, status: 0, stdout: lines.join('\n'), stderr: '' };
  }

  if (taskKey === 'git_log') {
    const res = runCommand('git', ['-c', 'core.pager=cat', 'log', '--oneline', '-10']);
    return { pass: res.pass, status: res.status, stdout: res.stdout, stderr: res.stderr };
  }

  if (taskKey === 'disk_usage') {
    // Count files and rough size in docs/ and dist/
    const countFiles = (dir) => {
      try {
        const res = runCommand('git', ['ls-files', '--', dir]);
        const files = (res.stdout || '').split('\n').filter(Boolean);
        return files.length;
      } catch { return -1; }
    };
    const docsCount = countFiles('docs/');
    const distCount = countFiles('dist_ai_math_web_pages/docs/');
    const lines = [
      `docs/ tracked files: ${docsCount}`,
      `dist_ai_math_web_pages/docs/ tracked files: ${distCount}`,
      `Reported at: ${nowIso()}`,
    ];
    return { pass: true, status: 0, stdout: lines.join('\n'), stderr: '' };
  }

  if (taskKey === 'freeform') {
    // Acknowledge the freeform request and list available commands
    const originalText = (cmdObj?.args?.original_text || cmdObj?.note || '').slice(0, 500);
    const tasks = allowList();
    const lines = [
      '## 收到自由文字請求',
      '',
      '> ' + originalText.split('\n').join('\n> '),
      '',
      '---',
      '',
      '目前的 Agent Command 系統支援以下 **預定義任務**：',
      '',
    ];
    for (const [k, v] of tasks) {
      if (k === 'freeform') continue;
      lines.push(`- \`${k}\` — ${v.desc}`);
    }
    lines.push(
      '',
      '### 如何使用',
      '在 Issue 中貼上以下格式即可自動執行：',
      '````',
      '```agent',
      '{"id":"cmd-唯一ID","task":"命令名"}',
      '```',
      '````',
      '',
      '> 提示：你也可以直接用中文描述，系統會自動比對關鍵字。',
      '> 例如寫「請驗證題庫」會自動執行 `validate_all`。',
      '',
      '如果你的請求是 **功能開發**（如新增題型、UI 改動），請在 Copilot Chat 中操作。',
    );
    return { pass: true, status: 0, stdout: lines.join('\n'), stderr: '' };
  }

  return { pass: false, status: 2, stdout: '', stderr: `unknown builtin: ${taskKey}` };
}

function runTask(taskKey, cmdObj) {
  const tasks = allowList();
  const spec = tasks.get(taskKey);
  if (!spec) {
    return { pass: false, status: 2, stdout: '', stderr: '', reason: `task not allowed: ${taskKey}` };
  }

  if (spec.kind === 'builtin') {
    const res = runBuiltinTask(taskKey);
    return { ...res, reason: res.pass ? '' : `builtin failed: ${taskKey}` };
  }

  if (spec.kind === 'py') {
    const py = pythonCmd();
    const res = runCommand(py, spec.argv);
    return { ...res, reason: res.pass ? '' : 'python task failed' };
  }

  if (spec.kind === 'node') {
    const res = runCommand('node', spec.argv);
    return { ...res, reason: res.pass ? '' : 'node task failed' };
  }

  if (spec.kind === 'npm') {
    const res = runCommand('npm', spec.argv);
    return { ...res, reason: res.pass ? '' : 'npm task failed' };
  }

  return { pass: false, status: 2, stdout: '', stderr: '', reason: `unsupported task kind: ${spec.kind}` };
}

function ghJson(args) {
  const res = runCommand(GH_CMD, args);
  if (!res.pass) {
    return { pass: false, status: res.status, obj: null, stdout: res.stdout, stderr: res.stderr };
  }
  try {
    return { pass: true, status: 0, obj: JSON.parse(String(res.stdout || '')), stdout: res.stdout, stderr: res.stderr };
  } catch (err) {
    return { pass: false, status: 2, obj: null, stdout: res.stdout, stderr: `invalid gh json: ${String(err?.message || err)}` };
  }
}

function ghCommentIssue(repo, issueNumber, body) {
  // Use gh api with JSON input to avoid Windows code-page issues with body-file.
  const bodyStr = String(body || '');
  const jsonPayload = JSON.stringify({ body: bodyStr });
  const tmpFile = path.join(process.cwd(), 'artifacts', '_gh_api_payload.json');
  fs.mkdirSync(path.dirname(tmpFile), { recursive: true });
  fs.writeFileSync(tmpFile, jsonPayload, 'utf8');
  const res = runCommand(GH_CMD, [
    'api', `repos/${repo}/issues/${issueNumber}/comments`,
    '--method', 'POST',
    '--input', tmpFile,
  ]);
  try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
  return res;
}

function ghCloseIssue(repo, issueNumber) {
  return runCommand(GH_CMD, ['issue', 'close', String(issueNumber), '--repo', repo]);
}

function listOpenIssues(repo, label, limit) {
  return ghJson(['issue', 'list', '--repo', repo, '--label', label, '--state', 'open', '--limit', String(limit), '--json', 'number,title,updatedAt,labels']);
}

function viewIssue(repo, issueNumber) {
  return ghJson(['issue', 'view', String(issueNumber), '--repo', repo, '--json', 'number,title,body,author,comments,updatedAt']);
}

function toAuthorLogin(authorObj) {
  if (!authorObj) return '';
  return String(authorObj.login || '').trim();
}

function extractCommandsFromIssue(issueObj) {
  const out = [];
  const issueAuthor = toAuthorLogin(issueObj.author);
  const issueNumber = issueObj.number;

  const bodyBlocks = extractAgentBlocks(issueObj.body);
  for (const b of bodyBlocks) {
    try {
      const obj = parseJsonWithObjectFallback(b, `issue#${issueNumber}:body`);
      const cmd = normalizeCommand(obj, {
        issue_number: issueNumber,
        source: 'issue_body',
        author: issueAuthor,
      });
      if (cmd) out.push(cmd);
    } catch {
      // ignore invalid blocks
    }
  }

  const comments = Array.isArray(issueObj.comments) ? issueObj.comments : [];
  for (const c of comments) {
    const author = toAuthorLogin(c.author);
    const commentId = c.id ?? null;
    const blocks = extractAgentBlocks(c.body);
    for (const b of blocks) {
      try {
        const obj = parseJsonWithObjectFallback(b, `issue#${issueNumber}:comment#${commentId}`);
        const cmd = normalizeCommand(obj, {
          issue_number: issueNumber,
          source: 'comment',
          comment_id: commentId,
          author,
        });
        if (cmd) out.push(cmd);
      } catch {
        // ignore invalid blocks
      }
    }
  }

  // --- Freeform fallback ---
  // If no valid ```agent``` blocks found anywhere, try freeform synthesis
  if (out.length === 0) {
    const freeformCmds = synthesizeFreeformCommands(issueObj);
    out.push(...freeformCmds);
  }

  return out;
}

function isAllowedAuthor(cmd, allowedAuthors) {
  if (!allowedAuthors || allowedAuthors.size === 0) return true;
  return allowedAuthors.has(String(cmd?.source?.author || ''));
}

function formatAck(cmd) {
  const note = cmd.note ? `\n\nNote: ${cmd.note}` : '';
  return [
    `ACK: received agent command`,
    `- id: ${cmd.id}`,
    `- task: ${cmd.task}`,
    `- source: ${cmd.source?.source || '-'}`,
    `- author: ${cmd.source?.author || '-'}`,
    note,
    `\nStatus: running...`,
    `\n(If you re-post the same id, it will be ignored to prevent double-runs.)`
  ].join('\n');
}

function formatResult(cmd, result, startedAtIso, finishedAtIso) {
  const ok = Boolean(result.pass);
  const title = ok ? 'DONE (pass)' : 'FAILED';
  const out = truncateLog(result.stdout);
  const err = truncateLog(result.stderr);
  return [
    `${title}: agent command`,
    `- id: ${cmd.id}`,
    `- task: ${cmd.task}`,
    `- started_at: ${startedAtIso}`,
    `- finished_at: ${finishedAtIso}`,
    `- exit_code: ${Number(result.status)}`,
    result.reason ? `- reason: ${result.reason}` : null,
    '',
    '---',
    'stdout (truncated):',
    '```',
    out || '(empty)',
    '```',
    'stderr (truncated):',
    '```',
    err || '(empty)',
    '```'
  ].filter(Boolean).join('\n');
}

async function mainOnce(opts) {
  ensureArtifacts();
  const statePath = opts.statePath;
  const state = readState(statePath);
  const executed = new Set(state.executed_ids || []);

  const listRes = listOpenIssues(opts.repo, opts.label, opts.limit);
  if (!listRes.pass) {
    const entry = {
      at: nowIso(),
      kind: 'poll_error',
      repo: opts.repo,
      label: opts.label,
      status: listRes.status,
      stderr: truncateLog(listRes.stderr),
    };
    appendRunLog(opts.runLogPath, entry);
    state.last_checked_at = nowIso();
    state.last_error = entry;
    writeState(statePath, state);
    return 1;
  }

  const issues = Array.isArray(listRes.obj) ? listRes.obj : [];
  let ran = 0;
  for (const it of issues) {
    const issueNumber = it.number;
    const viewRes = viewIssue(opts.repo, issueNumber);
    if (!viewRes.pass || !viewRes.obj) {
      appendRunLog(opts.runLogPath, {
        at: nowIso(),
        kind: 'view_error',
        issue_number: issueNumber,
        status: viewRes.status,
        stderr: truncateLog(viewRes.stderr),
      });
      continue;
    }

    const cmds = extractCommandsFromIssue(viewRes.obj);
    for (const cmd of cmds) {
      if (executed.has(cmd.id)) continue;
      if (!isAllowedAuthor(cmd, opts.allowedAuthors)) {
        executed.add(cmd.id);
        state.executed_ids = Array.from(executed);
        appendRunLog(opts.runLogPath, {
          at: nowIso(),
          kind: 'rejected',
          id: cmd.id,
          task: cmd.task,
          issue_number: issueNumber,
          reason: 'author not allowed',
          author: cmd.source?.author || '',
        });
        writeState(statePath, state);
        continue;
      }

      const startedAt = nowIso();
      if (!opts.dryRun) {
        ghCommentIssue(opts.repo, issueNumber, formatAck(cmd));
      }

      const result = opts.dryRun
        ? { pass: true, status: 0, stdout: '[dry-run] skipped execution', stderr: '' }
        : runTask(cmd.task, cmd);
      const finishedAt = nowIso();

      const runEntry = {
        at: finishedAt,
        kind: 'run',
        id: cmd.id,
        task: cmd.task,
        issue_number: issueNumber,
        author: cmd.source?.author || '',
        started_at: startedAt,
        finished_at: finishedAt,
        pass: Boolean(result.pass),
        status: Number(result.status),
      };
      appendRunLog(opts.runLogPath, runEntry);

      if (!opts.dryRun) {
        ghCommentIssue(opts.repo, issueNumber, formatResult(cmd, result, startedAt, finishedAt));
        if (cmd.close_issue && result.pass) {
          ghCloseIssue(opts.repo, issueNumber);
        }
      }

      executed.add(cmd.id);
      state.executed_ids = Array.from(executed);
      writeState(statePath, state);
      ran += 1;

      if (opts.maxRunsPerOnce > 0 && ran >= opts.maxRunsPerOnce) break;
    }
    if (opts.maxRunsPerOnce > 0 && ran >= opts.maxRunsPerOnce) break;
  }

  state.last_checked_at = nowIso();
  state.last_error = null;
  writeState(statePath, state);
  return 0;
}

async function main() {
  const repo = String(argValue('--repo', DEFAULT_REPO));
  const label = String(argValue('--label', DEFAULT_LABEL));
  const statePath = String(argValue('--state', STATE_PATH_DEFAULT));
  const runLogPath = String(argValue('--run-log', RUN_LOG_PATH_DEFAULT));
  const intervalSec = Number(argValue('--interval-sec', '60'));
  const limit = Number(argValue('--limit', '20'));
  const maxHours = Number(argValue('--max-hours', '0'));
  const maxRunsPerOnce = Number(argValue('--max-runs', '1'));
  const dryRun = hasFlag('--dry-run');
  const once = hasFlag('--once');

  const allowedAuthors = new Set();
  for (let i = 0; i < process.argv.length; i += 1) {
    if (process.argv[i] === '--allowed-author' && process.argv[i + 1]) {
      allowedAuthors.add(String(process.argv[i + 1]));
      i += 1;
    }
  }

  const opts = {
    repo,
    label,
    statePath,
    runLogPath,
    intervalSec,
    limit,
    maxHours,
    maxRunsPerOnce,
    dryRun,
    allowedAuthors,
  };

  if (once) {
    const code = await mainOnce(opts);
    process.exitCode = Number(code || 0);
    return;
  }

  const startedMs = Date.now();
  for (;;) {
    await mainOnce(opts);
    if (Number.isFinite(maxHours) && maxHours > 0) {
      const elapsedH = (Date.now() - startedMs) / 3600000;
      if (elapsedH >= maxHours) break;
    }
    await sleep(Math.max(5, intervalSec) * 1000);
  }
}

main().catch((err) => {
  ensureArtifacts();
  appendRunLog(RUN_LOG_PATH_DEFAULT, {
    at: nowIso(),
    kind: 'fatal',
    message: String(err?.message || err),
    stack: truncateLog(err?.stack || ''),
  });
  process.exitCode = 1;
});
