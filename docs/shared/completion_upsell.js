/* completion_upsell.js — lightweight post-session upsell overlay (empire modules)
   Auto-detects game completion via banner text observation.
   Shows once per browser session; skipped if daily-limit wall is already visible. */
(function(){
  var SKEY = 'aimath_comp_upsell_shown';
  if (sessionStorage.getItem(SKEY)) return;

  function buildOverlay(){
    var testCfg = window.AIMathABTest && window.AIMathABTest.getVariantConfig
      ? window.AIMathABTest.getVariantConfig('post_question_upsell')
      : null;
    var title = testCfg && testCfg.title ? testCfg.title : '做得好！繼續保持';
    var body = testCfg && testCfg.body ? testCfg.body : '升級後可以每天無限練習，解鎖 2,900+ 題完整題庫，搭配 AI 弱點分析更快進步。';
    var primaryLabel = testCfg && testCfg.primaryLabel ? testCfg.primaryLabel : '查看升級方案';
    var ov = document.createElement('div');
    ov.id = 'compUpsellOverlay';
    ov.setAttribute('style',
      'position:fixed;inset:0;z-index:450;background:rgba(0,0,0,0.7);' +
      'display:flex;align-items:center;justify-content:center;padding:24px;' +
      'animation:compFadeIn .35s ease');
    var card =
      '<div style="background:#161b22;border:1px solid #30363d;border-radius:16px;' +
      'max-width:400px;width:100%;padding:32px 24px;text-align:center">' +
      '<div style="font-size:2.4rem;margin-bottom:8px">&#x1F389;</div>' +
      '<div style="color:#fff;font-size:1.25rem;font-weight:700;margin-bottom:6px">' + title + '</div>' +
      '<p style="color:#8b949e;font-size:0.9rem;margin:0 0 18px;line-height:1.6">' +
      body + '</p>' +
      '<div style="display:flex;flex-direction:column;gap:10px">' +
      '<a id="compUpsellPrimary" href="../pricing/" style="display:block;background:#238636;color:#fff;' +
      'padding:12px;border-radius:8px;font-weight:700;text-decoration:none;font-size:0.95rem">' +
      '&#x1F4B0; ' + primaryLabel + '</a>' +
      '<a id="compUpsellSecondary" href="mailto:learnotaiwan@gmail.com?subject=%E5%85%8D%E8%B2%BB%E8%A9%A6%E7%94%A8" ' +
      'style="display:block;background:transparent;border:1px solid #58a6ff;color:#58a6ff;' +
      'padding:12px;border-radius:8px;font-weight:700;text-decoration:none;font-size:0.95rem">' +
      '&#x2709;&#xFE0F; 免費試用 7 天</a>' +
      '<button id="compUpsellClose" style="background:none;border:none;color:#8b949e;' +
      'cursor:pointer;font-size:0.85rem;padding:8px;margin-top:2px">下次再說</button>' +
      '</div></div>';
    ov.innerHTML = card;
    document.body.appendChild(ov);
    sessionStorage.setItem(SKEY, '1');
    var primary = document.getElementById('compUpsellPrimary');
    var secondary = document.getElementById('compUpsellSecondary');
    if (primary) {
      primary.onclick = function(){
        if (window.AIMathABTest) window.AIMathABTest.trackConversion('post_question_upsell', 'click_primary');
      };
    }
    if (secondary) {
      secondary.onclick = function(){
        if (window.AIMathABTest) window.AIMathABTest.trackConversion('post_question_upsell', 'click_secondary');
      };
    }
    document.getElementById('compUpsellClose').onclick = function(){ ov.remove(); };
    ov.onclick = function(e){ if (e.target === ov) ov.remove(); };
  }

  /* Inject animation keyframes */
  var sty = document.createElement('style');
  sty.textContent = '@keyframes compFadeIn{from{opacity:0}to{opacity:1}}';
  document.head.appendChild(sty);

  /* Observe game banner for completion text */
  function watchBanner(){
    var banner = document.getElementById('gBanner');
    if (!banner) return;
    var obs = new MutationObserver(function(muts){
      for (var i = 0; i < muts.length; i++){
        var txt = banner.textContent || '';
        if (txt.indexOf('\u7D50\u675F') !== -1 && txt.indexOf('\u5206\u6578') !== -1){
          /* "結束" + "分數" detected — game ended */
          /* Don't show if daily limit wall is visible */
          if (banner.innerHTML.indexOf('upgrade') !== -1) return;
          if (banner.innerHTML.indexOf('pricing') !== -1) return;
          obs.disconnect();
          setTimeout(buildOverlay, 2500);
          return;
        }
      }
    });
    obs.observe(banner, { childList: true, characterData: true, subtree: true });
  }

  /* Wait for DOM ready */
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', watchBanner);
  } else {
    watchBanner();
  }
})();
