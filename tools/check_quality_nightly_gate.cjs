#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const DOCS = path.join(ROOT, 'docs');
const ARTIFACTS = path.join(ROOT, 'artifacts');

const minL3Pct = Number(process.env.QUALITY_GATE_MIN_L3_PCT || '100');
const minCMPct = Number(process.env.QUALITY_GATE_MIN_CM_PCT || '100');

const MODULES = [
  { dir: 'exam-sprint', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-empire', file: 'bank.js', format: 'window' },
  { dir: 'life-applications-g5', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-life-pack2plus-empire', file: 'bank.js', format: 'window' },
  { dir: 'interactive-decimal-g5', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-life-pack1plus-empire', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-life-pack1-empire', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-life-pack2-empire', file: 'bank.js', format: 'window' },
  { dir: 'commercial-pack1-fraction-sprint', file: 'bank.js', format: 'iife', cmEligible: false },
  { dir: 'g5-grand-slam', file: 'bank.js', format: 'window' },
  { dir: 'ratio-percent-g5', file: 'bank.js', format: 'window' },
  { dir: 'volume-g5', file: 'bank.js', format: 'window' },
  { dir: 'fraction-g5', file: 'bank.js', format: 'window' },
  { dir: 'decimal-unit4', file: 'bank.js', format: 'window' },
  { dir: 'offline-math', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g56-core-foundation', file: 'g56_core_foundation.json', format: 'json' },
  { dir: 'interactive-g5-midterm1', file: 'bank.js', format: 'window' },
  { dir: 'interactive-g5-national-bank', file: 'bank.js', format: 'window' },
];

const BOILERPLATE_PATTERNS = [
  /請依前面步驟完成計算/,
  /請自行完成計算/,
  /請自己完成計算/,
  /依照前面提示完成/,
  /請自行檢查單位並寫出/,
  /自行檢查單位/,
  /最後請自行寫出答案/,
];

function isBoilerplate(text) {
  if (!text) return false;
  return BOILERPLATE_PATTERNS.some((pattern) => pattern.test(String(text)));
}

function loadBank(mod) {
  const fullPath = path.join(DOCS, mod.dir, mod.file);
  if (!fs.existsSync(fullPath)) {
    return [];
  }

  const raw = fs.readFileSync(fullPath, 'utf8');
  if (mod.format === 'json') {
    return JSON.parse(raw);
  }

  const sandbox = {
    window: {},
    console,
    Math,
    String,
    Number,
    Array,
    Object,
    JSON,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
  };
  vm.runInNewContext(raw, sandbox, { timeout: 5000 });
  for (const key of Object.keys(sandbox.window)) {
    const value = sandbox.window[key];
    if (Array.isArray(value)) {
      return value;
    }
  }
  return [];
}

function getHints(item) {
  if (Array.isArray(item.hints) && item.hints.length > 0) {
    return item.hints;
  }
  if (Array.isArray(item.steps) && item.steps.length > 0 && typeof item.steps[0] === 'string') {
    return item.steps;
  }
  if (Array.isArray(item.teacherSteps)) {
    return item.teacherSteps.map((step) => step.say || '');
  }
  return [];
}

function audit() {
  let totalL3 = 0;
  let boilerplateL3 = 0;
  let totalQuestions = 0;
  let cmEligibleQuestions = 0;
  let withCM = 0;
  const modules = [];

  for (const mod of MODULES) {
    const items = loadBank(mod);
    let moduleL3 = 0;
    let moduleBoilerplate = 0;
    let moduleWithCM = 0;

    items.forEach((item) => {
      totalQuestions += 1;
      if (mod.cmEligible !== false) {
        cmEligibleQuestions += 1;
        if (Array.isArray(item.common_mistakes) && item.common_mistakes.length > 0) {
          withCM += 1;
          moduleWithCM += 1;
        }
      }

      const hints = getHints(item);
      if (hints.length >= 3) {
        const lastHint = hints[hints.length - 1];
        totalL3 += 1;
        moduleL3 += 1;
        if (isBoilerplate(lastHint)) {
          boilerplateL3 += 1;
          moduleBoilerplate += 1;
        }
      }
    });

    modules.push({
      module: mod.dir,
      total: items.length,
      l3Count: moduleL3,
      l3Boilerplate: moduleBoilerplate,
      cmCount: moduleWithCM,
      l3Pct: moduleL3 ? Math.round(((moduleL3 - moduleBoilerplate) / moduleL3) * 100) : 100,
      cmPct: mod.cmEligible === false ? null : (items.length ? Math.round((moduleWithCM / items.length) * 100) : 100),
    });
  }

  return {
    totalQuestions,
    cmEligibleQuestions,
    withCM,
    totalL3,
    boilerplateL3,
    l3Pct: totalL3 ? Math.round(((totalL3 - boilerplateL3) / totalL3) * 100) : 100,
    cmPct: cmEligibleQuestions ? Math.round((withCM / cmEligibleQuestions) * 100) : 100,
    modules,
  };
}

const report = {
  generated_at: new Date().toISOString(),
  thresholds: { minL3Pct, minCMPct },
  metrics: audit(),
};

report.pass = report.metrics.l3Pct >= minL3Pct && report.metrics.cmPct >= minCMPct;

fs.mkdirSync(ARTIFACTS, { recursive: true });
fs.writeFileSync(
  path.join(ARTIFACTS, 'quality_nightly_gate.json'),
  JSON.stringify(report, null, 2) + '\n',
  'utf8'
);

console.log(`Quality nightly gate: L3=${report.metrics.l3Pct}% CM=${report.metrics.cmPct}% thresholds(L3>=${minL3Pct}, CM>=${minCMPct})`);
if (!report.pass) {
  const failingModules = report.metrics.modules.filter((mod) => mod.l3Pct < minL3Pct || (typeof mod.cmPct === 'number' && mod.cmPct < minCMPct));
  for (const mod of failingModules) {
    const cmLabel = typeof mod.cmPct === 'number' ? `${mod.cmPct}%` : 'n/a';
    console.log(`  FAIL ${mod.module}: L3=${mod.l3Pct}% CM=${cmLabel}`);
  }
  process.exit(1);
}
console.log('Quality nightly gate: PASS');
