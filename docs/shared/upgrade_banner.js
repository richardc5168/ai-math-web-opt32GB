/**
 * AIMathUpgradeBanner — lightweight upgrade prompt for free modules
 * Shows a dismissible bottom banner after user has been active for a while.
 * Auto-detects answer submissions by observing button clicks.
 * Uses localStorage to avoid showing too frequently.
 */
(function(){
  'use strict';
  var STORAGE_KEY = 'aimath_upgrade_banner_v1';
  var SHOW_AFTER_CLICKS = 15;
  var SHOW_AFTER_MS = 300000; // 5 minutes fallback
  var DISMISS_HOURS = 24;
  var EMAIL = 'learnotaiwan@gmail.com';
  var SUBJECT = encodeURIComponent('AI 數學家教 — 升級方案諮詢');

  function shouldShow(){
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var data = JSON.parse(raw);
        if (data.dismissed && (Date.now() - data.dismissed) < DISMISS_HOURS * 3600000) {
          return false;
        }
      }
    } catch(e){}
    return true;
  }

  function dismiss(){
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissed: Date.now() }));
    } catch(e){}
  }

  function createBanner(){
    if (document.getElementById('upgrade-banner')) return;
    var bar = document.createElement('div');
    bar.id = 'upgrade-banner';
    bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:9999;background:linear-gradient(135deg,#161b22 0%,#1c2333 100%);border-top:2px solid #8957e5;padding:14px 16px;display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;font-size:.88rem;box-shadow:0 -4px 16px rgba(0,0,0,0.5);';

    var text = document.createElement('span');
    text.style.cssText = 'color:#c9d1d9;';
    text.innerHTML = '\u2728 \u89E3\u9396 <strong style="color:#fff">6,900+</strong> \u984C\u5B8C\u6574\u984C\u5EAB\u3001AI \u5F31\u9EDE\u5206\u6790\u3001\u5BB6\u9577\u9031\u5831\u5373\u6642\u638C\u63E1\u5B78\u7FD2\u72C0\u6CC1';

    var btnWrap = document.createElement('span');
    btnWrap.style.cssText = 'display:flex;gap:8px;flex-wrap:nowrap;';

    var btn1 = document.createElement('a');
    btn1.href = '../pricing/';
    btn1.style.cssText = 'display:inline-block;background:linear-gradient(135deg,#8957e5,#a371f7);color:#fff;padding:7px 18px;border-radius:6px;font-weight:700;text-decoration:none;font-size:.85rem;white-space:nowrap;';
    btn1.textContent = '\ud83d\udcb0 \u67e5\u770b\u65b9\u6848';

    var btn2 = document.createElement('a');
    btn2.href = '../pricing/';
    btn2.style.cssText = 'display:inline-block;border:1px solid #8957e5;color:#a371f7;padding:6px 14px;border-radius:6px;font-weight:700;text-decoration:none;font-size:.85rem;white-space:nowrap;';
    btn2.textContent = '\u{1F680} \u514D\u8CBB\u8A66\u7528 7 \u5929';

    btnWrap.appendChild(btn1);
    btnWrap.appendChild(btn2);

    var close = document.createElement('button');
    close.style.cssText = 'background:none;border:none;color:#8b949e;font-size:1.2rem;cursor:pointer;padding:4px 8px;line-height:1;';
    close.textContent = '\u2715';
    close.setAttribute('aria-label', 'close');
    close.onclick = function(){
      bar.style.display = 'none';
      dismiss();
    };

    bar.appendChild(text);
    bar.appendChild(btnWrap);
    bar.appendChild(close);
    document.body.appendChild(bar);
  }

  if (!shouldShow()) return;

  // Auto-detect: count button clicks that look like answer submissions
  var clickCount = 0;
  var shown = false;
  document.addEventListener('click', function(e){
    if (shown) return;
    var t = e.target;
    if (!t) return;
    var tag = (t.tagName || '').toLowerCase();
    // Detect clicks on buttons/links that look like check/submit
    if (tag === 'button' || (tag === 'a' && t.className && t.className.indexOf('btn') >= 0)){
      var txt = (t.textContent || '').trim();
      if (txt.indexOf('\u6aa2\u67e5') >= 0 || txt.indexOf('\u78ba\u8a8d') >= 0 ||
          txt.indexOf('\u63d0\u4ea4') >= 0 || txt.indexOf('\u6b63\u78ba') >= 0 ||
          txt.indexOf('check') >= 0 || txt.length < 6) {
        clickCount++;
        if (clickCount >= SHOW_AFTER_CLICKS) {
          shown = true;
          createBanner();
        }
      }
    }
  }, true);

  // Fallback: show after 2 minutes of page usage
  setTimeout(function(){
    if (!shown && shouldShow()) {
      shown = true;
      createBanner();
    }
  }, SHOW_AFTER_MS);
})();
