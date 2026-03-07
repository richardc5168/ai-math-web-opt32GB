/* Module progress badge — reads localStorage attempts to show user's progress */
(function(){
  /* Detect module name from URL path */
  var path = location.pathname.replace(/\/index\.html.*$/, '').replace(/\/$/, '');
  var parts = path.split('/');
  var mod = parts[parts.length - 1];
  if (!mod) return;

  /* Read attempts from localStorage */
  var key = 'aimath_attempts_' + mod;
  var attempts = [];
  try { attempts = JSON.parse(localStorage.getItem(key) || '[]'); } catch(e){}
  if (!attempts.length) {
    /* Try alternative key format */
    try {
      var allKeys = Object.keys(localStorage);
      for (var i = 0; i < allKeys.length; i++) {
        if (allKeys[i].indexOf(mod) >= 0 && allKeys[i].indexOf('attempt') >= 0) {
          var d = JSON.parse(localStorage.getItem(allKeys[i]) || '[]');
          if (Array.isArray(d)) attempts = attempts.concat(d);
        }
      }
    } catch(e){}
  }

  var total = attempts.length;
  if (total === 0) return; /* No progress to show */

  var correct = 0;
  for (var j = 0; j < attempts.length; j++) {
    if (attempts[j].correct || attempts[j].ok || attempts[j].result === 'correct') correct++;
  }
  var pct = total > 0 ? Math.round(correct / total * 100) : 0;

  /* Create badge */
  var badge = document.createElement('div');
  badge.setAttribute('style',
    'position:fixed;bottom:72px;right:12px;background:rgba(13,17,23,0.95);' +
    'border:1px solid rgba(88,166,255,0.3);border-radius:12px;padding:10px 14px;' +
    'z-index:9990;font-size:.82rem;color:#c9d1d9;max-width:180px;text-align:center;' +
    'box-shadow:0 4px 16px rgba(0,0,0,0.3)'
  );

  var color = pct >= 80 ? '#3fb950' : pct >= 50 ? '#fbbf24' : '#8b949e';
  badge.innerHTML =
    '<div style="font-weight:700;color:' + color + ';font-size:1.3rem;margin-bottom:2px">' + pct + '%</div>' +
    '<div style="font-size:.75rem;color:#8b949e">\u7B54\u5C0D ' + correct + ' / ' + total + ' \u984C</div>';

  document.body.appendChild(badge);
})();
