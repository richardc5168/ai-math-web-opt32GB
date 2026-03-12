/**
 * AIMathDailyLimit — daily free question limiter for empire modules
 * Tracks usage per device per calendar day via localStorage.
 * Each module counts separately; total across all modules is limited.
 */
(function(){
  'use strict';
  var KEY = 'aimath_daily_limit_v1';
  var ENFORCE_KEY = 'aimath_daily_limit_enforced_v1';
  var FREE_LIMIT = 10;

  // Business policy: enforce daily limit for free users.
  // Free users get 10 questions/day; paid/trial users get unlimited.
  // To disable enforcement, set localStorage key to '0'
  // or set window.AIMathFlags.dailyLimitEnforced = false.
  function isLimitEnforced(){
    try {
      if (window.AIMathFlags && typeof window.AIMathFlags.dailyLimitEnforced === 'boolean') {
        return window.AIMathFlags.dailyLimitEnforced;
      }
      var v = localStorage.getItem(ENFORCE_KEY);
      if (v === '1') return true;
      if (v === '0') return false;
    } catch(e){}
    return true;
  }

  // A/B test: lazily override FREE_LIMIT when free_limit test is available
  function getLimit(){
    try {
      if (window.AIMathSubscription && window.AIMathSubscription.PLANS && window.AIMathSubscription.PLANS.free) {
        return Number(window.AIMathSubscription.PLANS.free.limit || FREE_LIMIT);
      }
      if (window.AIMathABTest) {
        var cfg = window.AIMathABTest.getVariantConfig('free_limit');
        if (cfg && typeof cfg.limit === 'number') return cfg.limit;
      }
    } catch(e){}
    return FREE_LIMIT;
  }
  var CONTACT_EMAIL = 'learnotaiwan@gmail.com';
  var CONTACT_SUBJECT = encodeURIComponent('AI 數學家教 — 升級方案諮詢');
  var CONTACT_BODY = encodeURIComponent('您好，我想了解 AI 數學家教的付費升級方案。\n\n孩子年級：\n目前使用模組：\n');

  function todayKey(){
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
  }

  function load(){
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch(e){ return null; }
  }

  function save(data){
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch(e){}
  }

  function getToday(){
    var data = load();
    var tk = todayKey();
    if (!data || data.date !== tk){
      data = { date: tk, used: 0 };
      save(data);
    }
    return data;
  }

  function getUsed(){
    return getToday().used;
  }

  function increment(){
    if (window.AIMathSubscription && window.AIMathSubscription.isPaid()){
      return getUsed();
    }
    var data = getToday();
    data.used += 1;
    save(data);
    return data.used;
  }

  function remaining(){
    if (!isLimitEnforced()) return -1;
    if (window.AIMathSubscription && window.AIMathSubscription.isPaid()) return -1;
    return Math.max(0, getLimit() - getUsed());
  }

  function isLimitReached(){
    if (!isLimitEnforced()) return false;
    // 付費用戶不限制
    if (window.AIMathSubscription && window.AIMathSubscription.isPaid()) return false;
    return getUsed() >= getLimit();
  }

  function buildUpgradeHTML(){
    if (!isLimitEnforced()) return '';
    if (window.AIMathSubscription && window.AIMathSubscription.isPaid()) return '';
    return '<div style="text-align:center;padding:20px 0;">'
      + '<div style="font-size:2rem;margin-bottom:8px;">&#x26A0;&#xFE0F;</div>'
      + '<div style="font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:8px;">'
      + '\u4eca\u65e5\u514d\u8cbb\u984c\u6578\u5df2\u7528\u5b8c\uff08' + getLimit() + ' \u984c\uff09'
      + '</div>'
      + '<div style="color:#8b949e;font-size:0.9rem;margin-bottom:16px;">'
      + '\u5347\u7d1a\u5f8c\u6bcf\u5929\u4e0d\u9650\u984c\u6578\uff0c\u89e3\u9396\u5b8c\u6574 2,900+ \u984c\u5eab\u3001\u5bb6\u9577\u9031\u5831\u3001AI \u88dc\u6551\u5efa\u8b70'
      + '</div>'
      + '<div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;">'
      + '<button onclick="if(window.AIMathSubscription){window.AIMathSubscription.trackUpgradeClick(\'standard\',{context:\'daily-limit\',cta_source:\'upgrade_daily_limit_trial\'});window.AIMathSubscription.beginTrialCheckout(\'standard\',{context:\'daily-limit\',cta_source:\'upgrade_daily_limit_trial\'});}location.reload();" style="display:inline-block;background:linear-gradient(135deg,#8957e5,#a371f7);color:#fff;padding:12px 24px;border:none;border-radius:8px;font-weight:700;text-decoration:none;font-size:0.95rem;cursor:pointer;">'
      + '\ud83c\udf81 \u514d\u8cbb\u8a66\u7528 7 \u5929</button>'
      + '<a href="../pricing/" onclick="if(window.AIMathSubscription){window.AIMathSubscription.trackUpgradeClick(\'standard\',{context:\'daily-limit\',cta_source:\'upgrade_daily_limit_pricing\'});}" style="display:inline-block;background:transparent;border:1px solid #58a6ff;color:#58a6ff;padding:12px 24px;border-radius:8px;font-weight:700;text-decoration:none;font-size:0.95rem;">'
      + '\u67e5\u770b\u65b9\u6848\u8207\u50f9\u683c</a>'
      + '</div>'
      + '<div style="color:#3fb950;font-size:0.82rem;margin-bottom:8px;">'
      + '\ud83d\udee1\ufe0f 7 \u5929\u5167\u4e0d\u6eff\u610f\u53ef\u5168\u984d\u9000\u8cbb\uff0c\u96f6\u98a8\u96aa'
      + '</div>'
      + '<div style="color:#8b949e;font-size:0.78rem;">'
      + '\u6216\u660e\u5929\u518d\u4f86\u7e7c\u7e8c\u514d\u8cbb\u7df4\u7fd2 ' + getLimit() + ' \u984c'
      + '</div>'
      + '</div>';
  }

  function buildCounterHTML(){
    if (!isLimitEnforced()){
      return '<div style="display:flex;align-items:center;gap:8px;font-size:0.8rem;color:#3fb950;">'
        + '<span>今日題數</span>'
        + '<span style="display:inline-block;padding:2px 10px;border-radius:999px;background:rgba(63,185,80,0.15);color:#3fb950;font-weight:700;">無上限</span>'
        + '</div>';
    }
    if (window.AIMathSubscription && window.AIMathSubscription.isPaid()){
      return '<div style="display:flex;align-items:center;gap:8px;font-size:0.8rem;color:#3fb950;">'
        + '<span>\u4eca\u65e5\u984c\u6578</span>'
        + '<span style="display:inline-block;padding:2px 10px;border-radius:999px;background:rgba(63,185,80,0.15);color:#3fb950;font-weight:700;">\u7121\u9650\u4f7f\u7528</span>'
        + '</div>';
    }
    var lim = getLimit();
    var used = getUsed();
    var left = Math.max(0, lim - used);
    var pct = Math.round((used / lim) * 100);
    var barColor = left <= 3 ? '#f85149' : left <= 5 ? '#d29922' : '#3fb950';
    return '<div style="display:flex;align-items:center;gap:8px;font-size:0.8rem;color:#8b949e;">'
      + '<span>\u4eca\u65e5\u514d\u8cbb</span>'
      + '<div style="flex:1;max-width:100px;height:6px;background:#30363d;border-radius:3px;overflow:hidden;">'
      + '<div style="width:' + pct + '%;height:100%;background:' + barColor + ';border-radius:3px;transition:width 0.3s;"></div>'
      + '</div>'
      + '<span style="color:' + barColor + ';font-weight:700;">' + used + '/' + lim + '</span>'
      + '</div>';
  }

  window.AIMathDailyLimit = {
    FREE_LIMIT: FREE_LIMIT,
    ENFORCE_KEY: ENFORCE_KEY,
    getLimit: getLimit,
    isLimitEnforced: isLimitEnforced,
    CONTACT_EMAIL: CONTACT_EMAIL,
    getUsed: getUsed,
    increment: increment,
    remaining: remaining,
    isLimitReached: isLimitReached,
    buildUpgradeHTML: buildUpgradeHTML,
    buildCounterHTML: buildCounterHTML
  };
})();
