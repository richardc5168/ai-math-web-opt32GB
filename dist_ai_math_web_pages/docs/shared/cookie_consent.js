/* Cookie / localStorage Consent Banner — self-contained IIFE
   Shows once; if accepted, never shows again (localStorage flag).
   No external dependencies. iOS-safe (no arrow functions, no optional chaining). */
(function(){
  if (localStorage.getItem('aimath_cookie_ok')) return;

  var css = document.createElement('style');
  css.textContent = [
    '#cookieConsent{position:fixed;bottom:0;left:0;right:0;z-index:9998;',
    'background:#161b22;border-top:1px solid #30363d;padding:14px 20px;',
    'display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;',
    'font-family:system-ui,-apple-system,sans-serif;font-size:.85rem;color:#c9d1d9;',
    'animation:ccSlideUp .4s ease}',
    '@keyframes ccSlideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}',
    '#cookieConsent a{color:#58a6ff;text-decoration:underline}',
    '#cookieConsent button{border:none;border-radius:6px;padding:8px 20px;font-size:.85rem;',
    'font-weight:700;cursor:pointer}',
    '#ccAccept{background:#238636;color:#fff}',
    '#ccDecline{background:#21262d;color:#c9d1d9;border:1px solid #30363d}'
  ].join('');
  document.head.appendChild(css);

  var bar = document.createElement('div');
  bar.id = 'cookieConsent';
  bar.setAttribute('role', 'alert');
  bar.setAttribute('aria-label', '隱私權與 Cookie 通知');
  /* Resolve privacy page link relative to site root */
  var p = location.pathname;
  var base = p.indexOf('/ai-math-web/') !== -1 ? p.replace(/\/ai-math-web\/.*/, '/ai-math-web/') : '/';
  var privacyHref = base + 'privacy/';

  bar.innerHTML = '<span>本站使用 localStorage 儲存學習進度，不使用追蹤型 Cookie。繼續使用即表示同意我們的 <a href="' + privacyHref + '">隱私權政策</a>。</span>' +
    '<button id="ccAccept">我知道了</button>' +
    '<button id="ccDecline">拒絕</button>';
  document.body.appendChild(bar);

  document.getElementById('ccAccept').addEventListener('click', function(){
    localStorage.setItem('aimath_cookie_ok', '1');
    bar.parentNode.removeChild(bar);
  });
  document.getElementById('ccDecline').addEventListener('click', function(){
    bar.parentNode.removeChild(bar);
  });
})();
