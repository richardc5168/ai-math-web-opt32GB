/**
 * AIMathDailyLimit — daily free question limiter for empire modules
 * Tracks usage per device per calendar day via localStorage.
 * Each module counts separately; total across all modules is limited.
 */
(function(){
  'use strict';
  var KEY = 'aimath_daily_limit_v1';
  var FREE_LIMIT = 10;
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
    var data = getToday();
    data.used += 1;
    save(data);
    return data.used;
  }

  function remaining(){
    return Math.max(0, FREE_LIMIT - getUsed());
  }

  function isLimitReached(){
    return getUsed() >= FREE_LIMIT;
  }

  function buildUpgradeHTML(){
    var mailLink = 'mailto:' + CONTACT_EMAIL + '?subject=' + CONTACT_SUBJECT + '&body=' + CONTACT_BODY;
    return '<div style="text-align:center;padding:20px 0;">'
      + '<div style="font-size:2rem;margin-bottom:8px;">\u26a0\ufe0f</div>'
      + '<div style="font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:8px;">'
      + '\u4eca\u65e5\u514d\u8cbb\u984c\u6578\u5df2\u7528\u5b8c\uff08' + FREE_LIMIT + ' \u984c\uff09'
      + '</div>'
      + '<div style="color:#8b949e;font-size:0.9rem;margin-bottom:16px;">'
      + '\u5347\u7d1a\u5f8c\u6bcf\u5929\u4e0d\u9650\u984c\u6578\uff0c\u89e3\u9396\u5b8c\u6574\u984c\u5eab\u3001\u5bb6\u9577\u9031\u5831\u3001AI \u88dc\u6551\u5efa\u8b70'
      + '</div>'
      + '<div style="margin-bottom:12px;">'
      + '<a href="' + mailLink + '" style="display:inline-block;background:linear-gradient(135deg,#8957e5,#a371f7);color:#fff;padding:12px 28px;border-radius:8px;font-weight:700;text-decoration:none;font-size:1rem;">'
      + '\u2709\ufe0f \u806f\u7e6b\u5347\u7d1a\uff08learnotaiwan@gmail.com\uff09</a>'
      + '</div>'
      + '<div style="color:#8b949e;font-size:0.78rem;">'
      + '\u6216\u660e\u5929\u518d\u4f86\u7e7c\u7e8c\u514d\u8cbb\u7df4\u7fd2 ' + FREE_LIMIT + ' \u984c'
      + '</div>'
      + '</div>';
  }

  function buildCounterHTML(){
    var used = getUsed();
    var left = remaining();
    var pct = Math.round((used / FREE_LIMIT) * 100);
    var barColor = left <= 3 ? '#f85149' : left <= 5 ? '#d29922' : '#3fb950';
    return '<div style="display:flex;align-items:center;gap:8px;font-size:0.8rem;color:#8b949e;">'
      + '<span>\u4eca\u65e5\u514d\u8cbb</span>'
      + '<div style="flex:1;max-width:100px;height:6px;background:#30363d;border-radius:3px;overflow:hidden;">'
      + '<div style="width:' + pct + '%;height:100%;background:' + barColor + ';border-radius:3px;transition:width 0.3s;"></div>'
      + '</div>'
      + '<span style="color:' + barColor + ';font-weight:700;">' + used + '/' + FREE_LIMIT + '</span>'
      + '</div>';
  }

  window.AIMathDailyLimit = {
    FREE_LIMIT: FREE_LIMIT,
    CONTACT_EMAIL: CONTACT_EMAIL,
    getUsed: getUsed,
    increment: increment,
    remaining: remaining,
    isLimitReached: isLimitReached,
    buildUpgradeHTML: buildUpgradeHTML,
    buildCounterHTML: buildCounterHTML
  };
})();
