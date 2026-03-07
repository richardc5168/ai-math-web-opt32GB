/* Page loader — inject loading spinner, auto-hide on load */
(function(){
  var s = document.createElement('style');
  s.textContent = '#_pl{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;background:#0b1020;display:flex;flex-direction:column;align-items:center;justify-content:center;transition:opacity .4s ease}#_pl.h{opacity:0;pointer-events:none}#_pl .r{width:40px;height:40px;border:3px solid #243055;border-top-color:#58a6ff;border-radius:50%;animation:_ps .8s linear infinite}#_pl .t{color:#9aa4b2;font-size:.82rem;margin-top:10px;font-family:system-ui,sans-serif}@keyframes _ps{to{transform:rotate(360deg)}}';
  document.head.appendChild(s);
  var d = document.createElement('div');
  d.id = '_pl';
  d.innerHTML = '<div class="r"></div><div class="t">\u8f09\u5165\u4e2d\u2026</div>';
  document.body.insertBefore(d, document.body.firstChild);
  window.addEventListener('load', function(){
    d.classList.add('h');
    setTimeout(function(){ d.remove(); }, 500);
  });
})();
