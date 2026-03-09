/**
 * daily_limit_wire.js — auto-wires AIMathDailyLimit to any practice module.
 *
 * Load AFTER daily_limit.js. Requires:
 *   - #banner element (for upgrade overlay)
 *   - #btnCheck / #btnNew (for intercept)
 *
 * Strategy:
 *   - Capture phase on btnCheck/btnNew: BLOCK interaction when limit reached
 *   - Bubble phase on btnCheck: increment() AFTER module handler processes
 *   - Counter bar rendered below the banner
 *
 * Empire modules (interactive-g5-*empire) already wire manually; this script
 * detects gDailyCounter and skips to avoid double-wiring.
 */
(function(){
  'use strict';
  var DL = window.AIMathDailyLimit;
  if (!DL) return;

  function ready(fn){
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function(){
    // Empire modules handle gating manually — skip entirely
    if (document.getElementById('gDailyCounter')) return;

    var banner = document.getElementById('banner');
    var btnCheck = document.getElementById('btnCheck');
    // Fallback for modules without #banner (e.g. offline-math): create one
    if (!banner){
      if (!btnCheck) return;
      banner = document.createElement('div');
      banner.id = 'dailyLimitBanner';
      banner.className = 'banner muted';
      banner.style.display = 'none';
      var insertRef = btnCheck.closest('.row') || btnCheck.parentNode;
      insertRef.parentNode.insertBefore(banner, insertRef);
    }

    // 1. Insert counter div after banner
    var counter = document.createElement('div');
    counter.id = 'dailyCounter';
    counter.style.marginTop = '6px';
    banner.parentNode.insertBefore(counter, banner.nextSibling);

    function updateCounter(){
      counter.innerHTML = DL.buildCounterHTML();
    }

    function showUpgrade(){
      banner.className = 'banner warn';
      banner.style.display = '';
      banner.innerHTML = DL.buildUpgradeHTML();
    }

    var btnNew = document.getElementById('btnNew');
    // Also handle modules that use btnSubmit instead of btnCheck
    var btnSubmit = btnCheck ? null : document.getElementById('btnSubmit');
    var submitBtn = btnCheck || btnSubmit;

    // 2. Capture phase — block buttons when limit reached
    function gateIfLimited(e){
      if (DL.isLimitReached()){
        e.stopImmediatePropagation();
        e.preventDefault();
        showUpgrade();
        return false;
      }
    }
    if (submitBtn) submitBtn.addEventListener('click', gateIfLimited, true);
    if (btnNew)    btnNew.addEventListener('click', gateIfLimited, true);

    // Also wrap .onclick handlers (for modules using onclick= instead of addEventListener)
    if (submitBtn && submitBtn.onclick){
      var origOnclick = submitBtn.onclick;
      submitBtn.onclick = function(e){
        if (DL.isLimitReached()){ showUpgrade(); return; }
        return origOnclick.call(this, e);
      };
    }

    // 3. Bubble phase on submit button — increment after module processes answer
    if (submitBtn){
      submitBtn.addEventListener('click', function(){
        if (DL.isLimitReached()) return; // already gated
        DL.increment();
        updateCounter();
        // Track question_submit + question_correct
        if (window.AIMathAnalytics){
          var module = location.pathname.replace(/\/$/, '').split('/').pop() || 'unknown';
          window.AIMathAnalytics.track('question_submit', { module: module });
          // Detect correctness from banner class (ok=correct, bad=incorrect)
          if (banner && /\bok\b/.test(banner.className)){
            window.AIMathAnalytics.track('question_correct', { module: module });
          }
        }
        if (DL.isLimitReached()){
          showUpgrade();
        }
      }, false); // bubble phase — runs after module handler
    }

    // 3b. Track question_start when new question button clicked
    if (btnNew){
      btnNew.addEventListener('click', function(){
        if (DL.isLimitReached()) return;
        if (window.AIMathAnalytics){
          var module = location.pathname.replace(/\/$/, '').split('/').pop() || 'unknown';
          window.AIMathAnalytics.track('question_start', { module: module });
        }
      }, false);
    }

    // 4. Initial render
    updateCounter();

    // If already at limit on page load, show gate immediately
    if (DL.isLimitReached()){
      showUpgrade();
    }
  });
})();
