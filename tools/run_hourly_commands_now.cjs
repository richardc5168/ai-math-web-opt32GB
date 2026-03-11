#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync, spawn } = require('child_process');

const ROOT = process.cwd();
const COMMAND_FILE = path.join(ROOT, 'ops', 'hourly_commands.json');
const ARTIFACTS = path.join(ROOT, 'artifacts');
fs.mkdirSync(ARTIFACTS, { recursive: true });

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const longRunning = new Set([
  'optimize:g5g6:web:5h',
  'overnight:optimize',
  'idle:web:fraction-decimal:expand',
  'pipeline:agent-loop:run',
  'pipeline:generate:run',
  'pipeline:solver:test',
  'pipeline:coverage'
]);

const raw = fs.readFileSync(COMMAND_FILE, 'utf8');
const payload = JSON.parse(raw);
const commands = Array.isArray(payload.commands) ? payload.commands : [];
const scripts = [...new Set(commands
  .filter(c => c && c.enabled && c.action === 'npm_script' && String(c.value || '').trim())
  .map(c => String(c.value).trim()))];

const report = {
  started_at: new Date().toISOString(),
  command_file: 'ops/hourly_commands.json',
  total_scripts: scripts.length,
  results: []
};

function runSync(script) {
  const started = new Date().toISOString();
  const res = spawnSync(`${npmCmd} run ${script}`, {
    cwd: ROOT,
    encoding: 'utf8',
    timeout: 20 * 60 * 1000,
    maxBuffer: 20 * 1024 * 1024,
    shell: true,
  });
  const ended = new Date().toISOString();
  const pass = res.status === 0;
  const outFile = path.join(ARTIFACTS, `_hourly_${script.replace(/[^a-zA-Z0-9._-]/g, '_')}.log`);
  fs.writeFileSync(outFile, [res.stdout || '', res.stderr || ''].join('\n'), 'utf8');
  return {
    script,
    mode: 'sync',
    started_at: started,
    ended_at: ended,
    pass,
    exit_code: res.status,
    log_file: path.relative(ROOT, outFile).replace(/\\/g, '/'),
  };
}

function runBackground(script) {
  const started = new Date().toISOString();
  const outFile = path.join(ARTIFACTS, `_hourly_bg_${script.replace(/[^a-zA-Z0-9._-]/g, '_')}.log`);
  const out = fs.openSync(outFile, 'a');
  const child = spawn(`${npmCmd} run ${script}`, {
    cwd: ROOT,
    detached: true,
    stdio: ['ignore', out, out],
    shell: true,
  });
  child.unref();
  return {
    script,
    mode: 'background',
    started_at: started,
    ended_at: null,
    pass: true,
    exit_code: null,
    pid: child.pid,
    log_file: path.relative(ROOT, outFile).replace(/\\/g, '/'),
  };
}

for (const script of scripts) {
  try {
    if (longRunning.has(script)) {
      report.results.push(runBackground(script));
    } else {
      report.results.push(runSync(script));
    }
  } catch (err) {
    report.results.push({
      script,
      mode: 'sync',
      started_at: new Date().toISOString(),
      ended_at: new Date().toISOString(),
      pass: false,
      exit_code: 1,
      error: String(err && err.message ? err.message : err),
    });
  }
}

report.ended_at = new Date().toISOString();
report.pass_count = report.results.filter(r => r.pass).length;
report.fail_count = report.results.filter(r => !r.pass).length;

const outJson = path.join(ARTIFACTS, 'hourly_commands_run_report.json');
fs.writeFileSync(outJson, JSON.stringify(report, null, 2) + '\n', 'utf8');

console.log(JSON.stringify({
  total_scripts: report.total_scripts,
  pass_count: report.pass_count,
  fail_count: report.fail_count,
  background_started: report.results.filter(r => r.mode === 'background').length,
  report: 'artifacts/hourly_commands_run_report.json'
}, null, 2));
