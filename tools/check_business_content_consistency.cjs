const fs = require('fs');
const path = require('path');

function hasFlag(name) {
  return process.argv.includes(name);
}

function readText(relPath) {
  const p = path.join(process.cwd(), relPath);
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
}

function addIssue(issues, code, severity, file, reason, evidence) {
  issues.push({ code, severity, file, reason, evidence });
}

const dailyLimit = readText('docs/shared/daily_limit.js');
const pricing = readText('docs/pricing/index.html');
const commercial = readText('docs/commercial-pack1-fraction-sprint/index.html');
const parentReport = readText('docs/parent-report/index.html');
const subscription = readText('docs/shared/subscription.js');

const issues = [];
const limitDisabledByDefault = /function isLimitEnforced\([\s\S]*?return false;\s*}/.test(dailyLimit);
const pricingClaimsTenQuestions = /每日\s*10\s*題|每日10題|10 題免費練習/.test(pricing);
if (limitDisabledByDefault && pricingClaimsTenQuestions) {
  addIssue(
    issues,
    'FREE_LIMIT_COPY_MISMATCH',
    'high',
    'docs/pricing/index.html',
    '免費題數文案仍主張每日 10 題，但實作目前預設無上限。',
    'pricing mentions daily 10 questions while daily_limit is unenforced by default'
  );
}

const freeReportBasic = /free:\s*\{[^}]*reportLevel:\s*'basic'/.test(subscription);
const parentReportHasNoSubscriptionGate = !/canAccessFullReport|getPlanInfo\(|reportLevel|plan_status/.test(parentReport);
if (freeReportBasic && parentReportHasNoSubscriptionGate) {
  addIssue(
    issues,
    'FULL_REPORT_GATE_MISSING',
    'high',
    'docs/parent-report/index.html',
    '訂閱模型區分 basic/full report，但家長報告頁沒有明確 gating 邏輯。',
    'subscription defines basic/full report levels, but parent-report lacks access gate checks'
  );
}

const commercialUsesLocalUnlock = /isUnlocked\(|setUnlocked\(|saveAccess\(/.test(commercial);
const commercialLacksSubscriptionAlignment = !/AIMathSubscription|plan_status|canAccess/.test(commercial);
if (commercialUsesLocalUnlock && commercialLacksSubscriptionAlignment) {
  addIssue(
    issues,
    'UNLOCK_STATE_NOT_ALIGNED',
    'medium',
    'docs/commercial-pack1-fraction-sprint/index.html',
    '內容包解鎖依賴本機狀態，可能出現頁面已解鎖但全域方案仍是 free。',
    'commercial pack uses local unlock helpers without shared subscription state checks'
  );
}

const report = {
  generated_at: new Date().toISOString(),
  summary: {
    issue_count: issues.length,
    health: issues.length === 0 ? 'strong' : (issues.some((x) => x.severity === 'high') ? 'improve' : 'watch')
  },
  issues
};

const md = [
  '# Business Content Consistency Report',
  '',
  `- generated_at: ${report.generated_at}`,
  `- issue_count: ${report.summary.issue_count}`,
  `- health: ${report.summary.health}`,
  '',
  '## Issues',
  ...(issues.length ? issues.map((issue) => `- [${issue.severity}] ${issue.code} @ ${issue.file}: ${issue.reason}`) : ['- none'])
].join('\n');

fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'business_content_consistency.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'business_content_consistency.md'), md, 'utf8');

console.log(JSON.stringify({
  summary: 'business content consistency checked',
  json: 'artifacts/business_content_consistency.json',
  md: 'artifacts/business_content_consistency.md',
  issue_count: report.summary.issue_count,
  health: report.summary.health
}, null, 2));

if (hasFlag('--strict') && issues.length) {
  process.exit(1);
}
