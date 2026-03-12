const fs = require('fs');
const path = require('path');

const EVENT_ALIASES = {
  weekly_report_view: 'report_open',
  checkout_success: 'paid_active',
  subscription_expired: 'expired',
  subscription_force_expire: 'expired'
};

const BUSINESS_EVENTS = [
  'pricing_view',
  'trial_start',
  'upgrade_click',
  'report_open',
  'weekly_report_copy',
  'redeem_success',
  'redeem_fail',
  'paid_active',
  'expired',
  'task_center_open'
];

function hasFlag(name) {
  return process.argv.includes(name);
}

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx < 0 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function readJson(relPath, fallback = null) {
  const p = path.join(process.cwd(), relPath);
  if (!fs.existsSync(p)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return fallback;
  }
}

function round3(value) {
  return Math.round(Number(value || 0) * 1000) / 1000;
}

function safeRate(num, den) {
  const n = Number(num || 0);
  const d = Number(den || 0);
  if (!d) return null;
  return round3(n / d);
}

function normalizeEventName(name) {
  const raw = String(name || '').trim();
  return EVENT_ALIASES[raw] || raw;
}

function loadEvents() {
  const explicit = argValue('--in', '');
  const candidates = explicit ? [explicit] : [
    'artifacts/analytics_events_latest.json',
    'artifacts/analytics_events.json',
    'artifacts/analytics_seed_events.json'
  ];
  for (const rel of candidates) {
    const parsed = readJson(rel, null);
    if (!parsed) continue;
    if (Array.isArray(parsed)) return { path: rel, events: parsed };
    if (Array.isArray(parsed.events)) return { path: rel, events: parsed.events };
  }
  return { path: null, events: [] };
}

function summarizeWindow(events, sinceMs) {
  const now = Date.now();
  const filtered = events.filter((event) => Number(event && event.ts || 0) >= now - sinceMs);
  const counts = Object.fromEntries(BUSINESS_EVENTS.map((name) => [name, 0]));
  const activeUsers = new Set();
  const returnUsers = new Set();
  const highIntentPages = new Map();

  filtered.forEach((event) => {
    const normalized = normalizeEventName(event && event.event);
    if (counts[normalized] != null) counts[normalized] += 1;
    if (/question_|task_center_open|report_open|pricing_view|trial_start|upgrade_click|redeem_success/.test(normalized)) {
      if (event && event.user_id) activeUsers.add(event.user_id);
    }
    if (normalized === 'return_next_week' && event && event.user_id) {
      returnUsers.add(event.user_id);
    }
    if (counts[normalized] != null) {
      const page = String((event && event.page) || ((event && event.data && event.data.page) || 'unknown'));
      highIntentPages.set(page, (highIntentPages.get(page) || 0) + 1);
    }
  });

  const topHighIntentPages = [...highIntentPages.entries()]
    .map(([page, count]) => ({ page, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  const topFrictionPoints = [];
  if (counts.redeem_fail > 0) {
    topFrictionPoints.push({ id: 'redeem_fail', count: counts.redeem_fail, reason: '兌換失敗會中斷成交。' });
  }
  if (counts.upgrade_click > counts.trial_start) {
    topFrictionPoints.push({ id: 'upgrade_drop_after_click', count: counts.upgrade_click - counts.trial_start, reason: '升級點擊後沒有進到試用或付款。' });
  }
  if (counts.expired > counts.paid_active) {
    topFrictionPoints.push({ id: 'expired_without_recovery', count: counts.expired, reason: '到期數高於啟用數，續費機制偏弱。' });
  }

  const weeklyActiveStudents = activeUsers.size;
  const summary = {
    insufficient_data: filtered.length === 0,
    event_count: filtered.length,
    counts,
    trial_start_rate: safeRate(counts.trial_start, counts.upgrade_click),
    upgrade_click_rate: safeRate(counts.upgrade_click, counts.pricing_view),
    report_open_rate: safeRate(counts.report_open, weeklyActiveStudents),
    redeem_success_rate: safeRate(counts.redeem_success, counts.redeem_success + counts.redeem_fail),
    weekly_active_students: weeklyActiveStudents,
    retention_7d_proxy: safeRate(returnUsers.size, weeklyActiveStudents),
    top_high_intent_pages: topHighIntentPages,
    top_friction_points: topFrictionPoints.slice(0, 3),
    health: 'insufficient_data'
  };

  if (!summary.insufficient_data) {
    summary.health = 'watch';
    if ((summary.upgrade_click_rate == null || summary.upgrade_click_rate >= 0.15)
      && (summary.trial_start_rate == null || summary.trial_start_rate >= 0.35)
      && (summary.redeem_success_rate == null || summary.redeem_success_rate >= 0.6)) {
      summary.health = 'strong';
    } else if ((summary.upgrade_click_rate != null && summary.upgrade_click_rate < 0.05)
      || (summary.trial_start_rate != null && summary.trial_start_rate < 0.15)
      || (summary.redeem_success_rate != null && summary.redeem_success_rate < 0.3)) {
      summary.health = 'improve';
    }
  }

  return summary;
}

const loaded = loadEvents();
const summary = {
  generated_at: new Date().toISOString(),
  source: loaded.path,
  windows: {
    daily: summarizeWindow(loaded.events, 86400000),
    d7: summarizeWindow(loaded.events, 7 * 86400000)
  }
};

const md = [
  '# Business Funnel Summary',
  '',
  `- generated_at: ${summary.generated_at}`,
  `- source: ${summary.source || 'none'}`,
  '',
  '## Daily',
  `- health: ${summary.windows.daily.health}`,
  `- insufficient_data: ${summary.windows.daily.insufficient_data}`,
  ...BUSINESS_EVENTS.map((name) => `- ${name}: ${summary.windows.daily.counts[name]}`),
  '',
  '## 7-Day Funnel',
  `- health: ${summary.windows.d7.health}`,
  `- insufficient_data: ${summary.windows.d7.insufficient_data}`,
  `- trial_start_rate: ${summary.windows.d7.trial_start_rate == null ? 'insufficient_data' : summary.windows.d7.trial_start_rate}`,
  `- upgrade_click_rate: ${summary.windows.d7.upgrade_click_rate == null ? 'insufficient_data' : summary.windows.d7.upgrade_click_rate}`,
  `- report_open_rate: ${summary.windows.d7.report_open_rate == null ? 'insufficient_data' : summary.windows.d7.report_open_rate}`,
  `- redeem_success_rate: ${summary.windows.d7.redeem_success_rate == null ? 'insufficient_data' : summary.windows.d7.redeem_success_rate}`,
  `- weekly_active_students: ${summary.windows.d7.weekly_active_students}`,
  `- retention_7d_proxy: ${summary.windows.d7.retention_7d_proxy == null ? 'insufficient_data' : summary.windows.d7.retention_7d_proxy}`,
  '',
  '## Top High Intent Pages',
  ...(summary.windows.d7.top_high_intent_pages.length
    ? summary.windows.d7.top_high_intent_pages.map((item) => `- ${item.page}: ${item.count}`)
    : ['- none']),
  '',
  '## Top Friction Points',
  ...(summary.windows.d7.top_friction_points.length
    ? summary.windows.d7.top_friction_points.map((item) => `- ${item.id}: ${item.count} (${item.reason})`)
    : ['- none'])
].join('\n');

fs.mkdirSync(path.join(process.cwd(), 'artifacts'), { recursive: true });
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'business_funnel_summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(process.cwd(), 'artifacts', 'business_funnel_summary.md'), md, 'utf8');

console.log(JSON.stringify({
  summary: 'business funnel summary generated',
  json: 'artifacts/business_funnel_summary.json',
  md: 'artifacts/business_funnel_summary.md',
  source: summary.source,
  daily_health: summary.windows.daily.health,
  d7_health: summary.windows.d7.health
}, null, 2));

if (hasFlag('--gate') && !summary.windows.d7.insufficient_data && summary.windows.d7.health === 'improve') {
  process.exit(1);
}
