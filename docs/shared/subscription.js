/**
 * AIMathSubscription — 前端訂閱狀態管理
 *
 * 儲存 key: aimath_subscription_v1
 * 方案狀態流：free → checkout_pending → trial / paid_active → expired
 *
 * Mock mode: 未設定 payment_provider.js 時自動啟用模擬；設定後切入 Stripe 真實金流。
 * 所有狀態變更都會觸發 analytics event（如果 AIMathAnalytics 可用）。
 * 依賴（可選）：firebase_config.js、auth_parent.js、payment_provider.js
 */
(function(){
  'use strict';
  var KEY = 'aimath_subscription_v1';
  var UNLIMITED_STUDENT_NAMES = {
    RICHKAI: true
  };
  var CTA_SOURCE_BY_CONTEXT = {
    'generic': 'upgrade_generic',
    'post-question': 'upgrade_post_question',
    'parent-report': 'upgrade_parent_report',
    'weakness': 'upgrade_weakness',
    'daily-limit': 'upgrade_daily_limit',
    'pricing': 'pricing_page',
    'pricing-standard': 'pricing_standard_trial',
    'pricing-family': 'pricing_family_trial'
  };

  /* ─── 方案定義 ─── */
  var PLANS = {
    free:     { name: '免費版', price: 0,   limit: -1, reportLevel: 'basic',  starPack: false },
    standard: { name: '標準版', price: 299, limit: -1, reportLevel: 'full',   starPack: true  },
    family:   { name: '家庭版', price: 499, limit: -1, reportLevel: 'full',   starPack: true  }
  };

  var TRIAL_DAYS = 7;

  /* ─── Mock Mode 判斷 ─── */
  function isMockMode(){
    // 當 AIMathPayment 已設定 Stripe 金鑰時，進入真實金流模式
    if (window.AIMathPayment && window.AIMathPayment.isConfigured()) return false;
    return true;
  }

  /* ─── 預設訂閱 ─── */
  function defaultSub(){
    return {
      plan_type: 'free',
      plan_status: 'free',         // free | trial | checkout_pending | paid_active | expired
      trial_start: null,           // ISO timestamp
      paid_start: null,
      expire_at: null,
      mock_mode: isMockMode()
    };
  }

  /* ─── 同步訂閱狀態到 student_auth ─── */
  function syncStudentProfile(sub){
    try {
      var patch = {
        plan_type: sub.plan_type,
        plan_status: sub.plan_status,
        trial_start: sub.trial_start,
        paid_start: sub.paid_start,
        expire_at: sub.expire_at,
        mock_mode: !!sub.mock_mode,
        subscription_updated_at: new Date().toISOString()
      };
      if (window.AIMathStudentAuth && typeof window.AIMathStudentAuth.isLoggedIn === 'function' && window.AIMathStudentAuth.isLoggedIn() && typeof window.AIMathStudentAuth.patchCurrentStudent === 'function') {
        window.AIMathStudentAuth.patchCurrentStudent(patch);
        return;
      }
      var raw = localStorage.getItem('aimath_student_auth_v1');
      if (!raw) return;
      var current = JSON.parse(raw);
      if (!current || !current.name || !current.pin) return;
      localStorage.setItem('aimath_student_auth_v1', JSON.stringify(Object.assign({}, current, patch, {
        updated_at: patch.subscription_updated_at
      })));
    } catch(e){}
  }

  /* ─── 同步到 Firestore（家長帳號） ─── */
  function syncToBackend(sub){
    syncStudentProfile(sub);
    if (window.AIMathParentAuth && window.AIMathParentAuth.isLoggedIn()){
      window.AIMathParentAuth.syncSubscription(sub);
    }
  }

  function trackStatusTransition(previousStatus, sub, meta, eventName, extra){
    var payload = buildEventPayload(sub.plan_type, meta, extra);
    payload.previous_status = previousStatus || 'free';
    payload.next_status = sub.plan_status;
    payload.plan_name = (PLANS[sub.plan_type] || PLANS.free).name;
    trackEvent('subscription_status_change', payload);
    if (eventName) trackEvent(eventName, payload);
  }

  /* ─── localStorage 讀寫 ─── */
  function load(){
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch(e){ return null; }
  }

  function save(sub){
    try { localStorage.setItem(KEY, JSON.stringify(sub)); } catch(e){}
    syncToBackend(sub);
  }

  function normalizeStudentName(name){
    var value = String(name || '');
    try {
      if (value.normalize) value = value.normalize('NFKC');
    } catch(e){}
    return value.trim().replace(/\s+/g, ' ').toUpperCase();
  }

  function getCurrentStudentName(){
    try {
      if (window.AIMathStudentAuth && typeof window.AIMathStudentAuth.getCurrentStudent === 'function') {
        var student = window.AIMathStudentAuth.getCurrentStudent();
        return normalizeStudentName(student && student.name);
      }
    } catch(e){}
    return '';
  }

  function hasUnlimitedAccess(){
    var name = getCurrentStudentName();
    return !!name && Object.prototype.hasOwnProperty.call(UNLIMITED_STUDENT_NAMES, name);
  }

  function getEffectiveSub(){
    var sub = getSub();
    if (!hasUnlimitedAccess()) return sub;
    return {
      plan_type: 'standard',
      plan_status: 'paid_active',
      trial_start: sub.trial_start,
      paid_start: sub.paid_start || sub.trial_start || null,
      expire_at: null,
      mock_mode: true,
      entitled_via: 'student_name',
      entitled_student: getCurrentStudentName()
    };
  }

  function defaultSourceForContext(context){
    return CTA_SOURCE_BY_CONTEXT[String(context || 'generic')] || CTA_SOURCE_BY_CONTEXT.generic;
  }

  function normalizeMeta(meta){
    if (typeof meta === 'string') meta = { cta_source: meta };
    meta = meta || {};
    return {
      context: String(meta.context || 'generic'),
      cta_source: String(meta.cta_source || meta.source || defaultSourceForContext(meta.context))
    };
  }

  function buildEventPayload(planType, meta, extra){
    var sub = getEffectiveSub();
    var normalized = normalizeMeta(meta);
    var payload = {
      plan: planType || sub.plan_type,
      plan_type: planType || sub.plan_type,
      plan_status: sub.plan_status,
      context: normalized.context,
      cta_source: normalized.cta_source
    };
    var ext = extra || {};
    for (var key in ext){
      if (Object.prototype.hasOwnProperty.call(ext, key) && ext[key] != null){
        payload[key] = ext[key];
      }
    }
    return payload;
  }

  function getSub(){
    var sub = load();
    if (!sub) {
      sub = defaultSub();
      save(sub);
    }
    // 自動檢查過期
    if (sub.expire_at && new Date(sub.expire_at).getTime() < Date.now()){
      if (sub.plan_status === 'trial' || sub.plan_status === 'paid_active'){
        sub.plan_status = 'expired';
        save(sub);
        trackEvent('subscription_expired', buildEventPayload(sub.plan_type, {
          context: 'subscription-expiry',
          cta_source: 'subscription_expiry_auto'
        }, {
          expire: sub.expire_at
        }));
      }
    }
    return sub;
  }

  /* ─── 事件追蹤（如果 AIMathAnalytics 可用） ─── */
  function trackEvent(name, data){
    if (window.AIMathAnalytics && typeof window.AIMathAnalytics.track === 'function'){
      window.AIMathAnalytics.track(name, data);
    }
  }

  /* ─── 狀態查詢 ─── */
  function getPlanType(){
    return getEffectiveSub().plan_type;
  }

  function getPlanStatus(){
    return getEffectiveSub().plan_status;
  }

  function isPaid(){
    var s = getEffectiveSub().plan_status;
    return s === 'paid_active' || s === 'trial';
  }

  function isTrial(){
    return getEffectiveSub().plan_status === 'trial';
  }

  function isExpired(){
    return getEffectiveSub().plan_status === 'expired';
  }

  function isFreePlan(){
    return getEffectiveSub().plan_status === 'free';
  }

  function canStartTrial(){
    var s = getEffectiveSub().plan_status;
    return s === 'free' || s === 'expired';
  }

  function getPlanInfo(){
    var sub = getEffectiveSub();
    var plan = PLANS[sub.plan_type] || PLANS.free;
    return {
      plan_type: sub.plan_type,
      plan_status: sub.plan_status,
      plan_name: plan.name,
      price: plan.price,
      daily_limit: plan.limit,
      report_level: plan.reportLevel,
      star_pack: plan.starPack,
      trial_start: sub.trial_start,
      paid_start: sub.paid_start,
      expire_at: sub.expire_at,
      trial_remaining_days: (sub.trial_start && sub.expire_at) ? Math.max(0, Math.ceil((new Date(sub.expire_at).getTime() - Date.now()) / 86400000)) : null,
      entitled_via: sub.entitled_via || null,
      entitled_student: sub.entitled_student || null
    };
  }

  function trackUpgradeClick(planType, meta){
    trackEvent('upgrade_click', buildEventPayload(planType, meta));
  }

  /* ─── 狀態變更 ─── */
  function startTrial(planType, meta){
    var plan = planType || 'standard';
    if (!PLANS[plan]) plan = 'standard';
    var now = new Date();
    var expire = new Date(now.getTime() + TRIAL_DAYS * 86400000);
    var sub = getSub();
    var previousStatus = sub.plan_status;
    sub.plan_type = plan;
    sub.plan_status = 'trial';
    sub.trial_start = now.toISOString();
    sub.expire_at = expire.toISOString();
    save(sub);
    trackStatusTransition(previousStatus, sub, meta, 'trial_start', {
      expire: sub.expire_at,
      trial_start: sub.trial_start
    });
    // A/B conversion: trial start is conversion for trial_btn_color + free_limit
    if (window.AIMathABTest){
      window.AIMathABTest.trackConversion('hero_headline', 'trial_start', { plan: plan });
      window.AIMathABTest.trackConversion('free_plan_message', 'trial_start', { plan: plan });
      window.AIMathABTest.trackConversion('trial_btn_color', 'trial_start', { plan: plan });
      window.AIMathABTest.trackConversion('free_limit', 'trial_start', { plan: plan });
    }
    return sub;
  }

  function startCheckout(planType, meta){
    var sub = getSub();
    var previousStatus = sub.plan_status;
    sub.plan_type = planType || sub.plan_type || 'standard';
    sub.plan_status = 'checkout_pending';
    sub.last_checkout_at = new Date().toISOString();
    save(sub);
    trackStatusTransition(previousStatus, sub, meta, 'checkout_start', {
      last_checkout_at: sub.last_checkout_at
    });
    return sub;
  }

  function confirmPayment(planType, meta){
    var now = new Date();
    var expire = new Date(now.getTime() + 30 * 86400000); // 月繳
    var sub = getSub();
    var previousStatus = sub.plan_status;
    sub.plan_type = planType || sub.plan_type || 'standard';
    sub.plan_status = 'paid_active';
    sub.paid_start = now.toISOString();
    sub.expire_at = expire.toISOString();
    save(sub);
    trackStatusTransition(previousStatus, sub, meta, 'checkout_success', {
      expire: sub.expire_at,
      paid_start: sub.paid_start
    });
    // A/B conversion: checkout success
    if (window.AIMathABTest){
      window.AIMathABTest.trackConversion('hero_headline', 'checkout_success', { plan: sub.plan_type });
      window.AIMathABTest.trackConversion('free_plan_message', 'checkout_success', { plan: sub.plan_type });
      window.AIMathABTest.trackConversion('trial_btn_color', 'checkout_success', { plan: sub.plan_type });
      window.AIMathABTest.trackConversion('free_limit', 'checkout_success', { plan: sub.plan_type });
    }
    return sub;
  }

  function cancelSubscription(meta){
    var sub = getSub();
    var previousStatus = sub.plan_status;
    sub.plan_status = 'expired';
    save(sub);
    trackStatusTransition(previousStatus, sub, meta, 'subscription_cancel');
    return sub;
  }

  function expireNow(meta){
    var sub = getSub();
    var previousStatus = sub.plan_status;
    sub.plan_status = 'expired';
    save(sub);
    trackStatusTransition(previousStatus, sub, meta, 'subscription_force_expire');
    return sub;
  }

  function resetToFree(){
    var previousStatus = getSub().plan_status;
    var sub = defaultSub();
    save(sub);
    trackStatusTransition(previousStatus, sub, {
      context: 'subscription-reset',
      cta_source: 'subscription_reset_manual'
    }, 'subscription_reset');
    return sub;
  }

  function beginTrialCheckout(planType, meta){
    startCheckout(planType, meta);
    return startTrial(planType, meta);
  }

  function activatePaidPlan(planType, meta){
    startCheckout(planType, meta);
    return confirmPayment(planType, meta);
  }

  /* ─── Feature Gating ─── */
  function canAccessStarPack(){
    return isPaid();
  }

  function canAccessFullReport(){
    var sub = getEffectiveSub();
    var plan = PLANS[sub.plan_type] || PLANS.free;
    return isPaid() && plan.reportLevel === 'full';
  }

  function getDailyLimit(){
    var sub = getEffectiveSub();
    var plan = PLANS[sub.plan_type] || PLANS.free;
    if (isPaid()) return -1; // 無限
    return plan.limit;
  }

  function canAccessModule(moduleId){
    // 免費模組：exam-sprint, fraction-g5 (基礎), offline-math
    var freeModules = ['exam-sprint', 'fraction-g5', 'offline-math', 'interactive-g56-core-foundation'];
    if (isPaid()) return true;
    return freeModules.indexOf(moduleId) >= 0;
  }

  /* ─── Upgrade CTA HTML ─── */
  function buildUpgradeCTA(context, options){
    var ctx = context || 'generic';
    var opts = options || {};
    var sub = getEffectiveSub();
    var trialPlan = opts.planType || 'standard';
    var normalized = normalizeMeta({ context: ctx, cta_source: opts.cta_source });
    var trialSource = normalized.cta_source + '_trial';
    var pricingSource = normalized.cta_source + '_pricing';

    if (isPaid()) return ''; // 已付費不顯示

    var msgs = {
      'post-question': '✨ 升級後不限題數，解鎖完整 2,900+ 題庫 + AI 補救建議',
      'parent-report': '📊 升級後查看完整學習週報、概念雷達、補救建議',
      'weakness': '🎯 升級後查看完整弱點分析 + 推薦練習題組',
      'daily-limit': '⚠️ 今日免費題數已用完，升級後每天不限題數',
      'generic': '🚀 升級解鎖完整題庫、家長週報、AI 補救建議'
    };

    var msg = msgs[ctx] || msgs.generic;

    var trialBtn = '';
    if (sub.plan_status === 'free'){
      trialBtn = '<button onclick="AIMathSubscription.trackUpgradeClick(\'' + trialPlan + '\',{context:\'' + ctx + '\',cta_source:\'' + trialSource + '\'});AIMathSubscription.beginTrialCheckout(\'' + trialPlan + '\',{context:\'' + ctx + '\',cta_source:\'' + trialSource + '\'});location.reload();" '
        + 'style="display:inline-block;background:linear-gradient(135deg,#8957e5,#a371f7);color:#fff;padding:10px 20px;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:.9rem;margin-right:8px;">'
        + '🎁 免費試用 7 天</button>';
    }

    return '<div class="aimath-upgrade-cta" style="background:linear-gradient(135deg,#161b22,#1c2333);border:1px solid #8957e5;border-radius:12px;padding:16px;margin:12px 0;text-align:center;">'
      + '<div style="color:#c9d1d9;font-size:.92rem;margin-bottom:12px;">' + msg + '</div>'
      + '<div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">'
      + trialBtn
      + '<a href="../pricing/" onclick="AIMathSubscription.trackUpgradeClick(\'' + trialPlan + '\',{context:\'' + ctx + '\',cta_source:\'' + pricingSource + '\'});" style="display:inline-block;border:1px solid #58a6ff;color:#58a6ff;padding:10px 20px;border-radius:8px;font-weight:700;text-decoration:none;font-size:.9rem;">'
      + '💰 查看方案</a>'
      + '</div>'
      + (sub.plan_status === 'expired' ? '<div style="color:#f85149;font-size:.8rem;margin-top:8px;">試用已到期，升級繼續使用完整功能</div>' : '')
      + '</div>';
  }

  /* ─── 同步到 Gist（附加到 student_auth cloud sync） ─── */
  function getSubForCloud(){
    return getSub();
  }

  /* ─── Export ─── */
  window.AIMathSubscription = {
    PLANS: PLANS,
    TRIAL_DAYS: TRIAL_DAYS,
    getPlanType: getPlanType,
    getPlanStatus: getPlanStatus,
    getPlanInfo: getPlanInfo,
    hasUnlimitedAccess: hasUnlimitedAccess,
    trackUpgradeClick: trackUpgradeClick,
    isPaid: isPaid,
    isTrial: isTrial,
    isExpired: isExpired,
    isFreePlan: isFreePlan,
    canStartTrial: canStartTrial,
    startTrial: startTrial,
    startCheckout: startCheckout,
    beginTrialCheckout: beginTrialCheckout,
    activatePaidPlan: activatePaidPlan,
    confirmPayment: confirmPayment,
    cancelSubscription: cancelSubscription,
    expireNow: expireNow,
    resetToFree: resetToFree,
    canAccessStarPack: canAccessStarPack,
    canAccessFullReport: canAccessFullReport,
    getDailyLimit: getDailyLimit,
    canAccessModule: canAccessModule,
    buildUpgradeCTA: buildUpgradeCTA,
    getSubForCloud: getSubForCloud,
    isMockMode: isMockMode
  };
})();
