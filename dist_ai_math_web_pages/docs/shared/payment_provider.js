/**
 * payment_provider.js — Stripe Checkout 金流串接
 *
 * 依賴：firebase_config.js (可選)、subscription.js
 *
 * 架構：
 *   前端 → Stripe Checkout (redirect) → Stripe webhook → Cloud Function
 *     → Firestore 更新 subscription 狀態
 *     → 前端偵測到狀態變更 → 解鎖功能
 *
 * 安裝步驟：
 *   1. 在 Stripe Dashboard 建立產品 + 價格
 *   2. 把 STRIPE_PUBLISHABLE_KEY 填入下方
 *   3. 把 Price ID 填入 PRICE_IDS
 *   4. 部署 Cloud Function (functions/stripe_webhook.js) 處理 webhook
 *   5. 在 Stripe Dashboard 設定 webhook endpoint
 */
(function(){
  'use strict';

  /* ─── Configuration ─── */
  var STRIPE_PUBLISHABLE_KEY = ''; // ← pk_live_... or pk_test_...
  var CHECKOUT_API_URL = '';       // ← Cloud Function URL: https://your-region-your-project.cloudfunctions.net/createCheckoutSession

  // Stripe Price IDs (from Stripe Dashboard)
  var PRICE_IDS = {
    standard_monthly: '', // ← price_...
    standard_yearly:  '', // ← price_...
    family_monthly:   '', // ← price_...
    family_yearly:    ''  // ← price_...
  };

  var _stripe = null;
  var _loading = false;

  /* ─── Helpers ─── */
  function isConfigured(){
    return !!(STRIPE_PUBLISHABLE_KEY && CHECKOUT_API_URL);
  }

  function loadStripeSDK(){
    if (window.Stripe) return Promise.resolve();
    return new Promise(function(resolve, reject){
      var s = document.createElement('script');
      s.src = 'https://js.stripe.com/v3/';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function getStripe(){
    if (_stripe) return _stripe;
    if (!window.Stripe || !STRIPE_PUBLISHABLE_KEY) return null;
    _stripe = window.Stripe(STRIPE_PUBLISHABLE_KEY);
    return _stripe;
  }

  /**
   * 取得當前使用者 UID（Firebase Auth 或 localStorage fallback）
   */
  function getCurrentUID(){
    if (window.AIMathParentAuth && window.AIMathParentAuth.isLoggedIn()){
      var user = window.AIMathParentAuth.getUser();
      return user ? user.uid : null;
    }
    // fallback: student auth
    if (window.AIMathStudentAuth && window.AIMathStudentAuth.isLoggedIn()){
      var student = window.AIMathStudentAuth.getCurrentStudent();
      return student ? 'student_' + (student.name || 'anon') : null;
    }
    return null;
  }

  /**
   * 建立 Stripe Checkout Session（透過 Cloud Function）
   *
   * @param {string} planType - 'standard' | 'family'
   * @param {string} billingPeriod - 'monthly' | 'yearly'
   * @param {Object} meta - { context, cta_source }
   * @returns {Promise<void>} — redirects to Stripe Checkout
   */
  function startCheckout(planType, billingPeriod, meta){
    if (_loading) return Promise.reject(new Error('結帳進行中'));
    if (!isConfigured()){
      console.warn('[Payment] Stripe not configured — falling back to mock');
      return _mockCheckout(planType, meta);
    }

    _loading = true;
    var priceKey = (planType || 'standard') + '_' + (billingPeriod || 'monthly');
    var priceId = PRICE_IDS[priceKey];
    if (!priceId){
      _loading = false;
      return Promise.reject(new Error('Invalid plan: ' + priceKey));
    }

    var uid = getCurrentUID();
    var parentEmail = '';
    if (window.AIMathParentAuth && window.AIMathParentAuth.isLoggedIn()){
      var user = window.AIMathParentAuth.getUser();
      parentEmail = user ? user.email : '';
    }

    // Track checkout start
    if (window.AIMathSubscription){
      window.AIMathSubscription.startCheckout(planType, meta);
    }
    if (window.AIMathAnalytics){
      window.AIMathAnalytics.track('stripe_checkout_start', {
        plan: planType,
        billing: billingPeriod,
        price_id: priceId
      });
    }

    return loadStripeSDK().then(function(){
      var stripe = getStripe();
      if (!stripe){
        _loading = false;
        return Promise.reject(new Error('Stripe SDK 載入失敗'));
      }

      // Call Cloud Function to create Checkout Session
      return fetch(CHECKOUT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          price_id: priceId,
          customer_uid: uid,
          customer_email: parentEmail,
          plan_type: planType,
          billing_period: billingPeriod,
          success_url: window.location.origin + '/docs/pricing/?checkout=success&plan=' + planType,
          cancel_url: window.location.origin + '/docs/pricing/?checkout=cancel'
        })
      }).then(function(res){
        if (!res.ok) throw new Error('建立結帳失敗 (' + res.status + ')');
        return res.json();
      }).then(function(data){
        if (!data.sessionId) throw new Error('No session ID returned');
        // Redirect to Stripe Checkout
        return stripe.redirectToCheckout({ sessionId: data.sessionId });
      }).then(function(result){
        if (result && result.error){
          throw new Error(result.error.message);
        }
      });
    }).catch(function(err){
      _loading = false;
      console.error('[Payment] Checkout error:', err);
      if (window.AIMathAnalytics){
        window.AIMathAnalytics.track('stripe_checkout_error', { error: err.message });
      }
      throw err;
    }).finally(function(){
      _loading = false;
    });
  }

  /**
   * Mock checkout fallback (when Stripe is not configured)
   */
  function _mockCheckout(planType, meta){
    if (window.AIMathSubscription){
      window.AIMathSubscription.beginTrialCheckout(planType, meta);
    }
    return Promise.resolve();
  }

  /**
   * 處理 Checkout 成功回調（pricing 頁面回來時呼叫）
   */
  function handleCheckoutReturn(){
    var params = new URLSearchParams(window.location.search);
    var checkout = params.get('checkout');
    var plan = params.get('plan');

    if (checkout === 'success' && plan){
      // Stripe webhook 應該已經更新了 Firestore
      // 這裡做前端狀態同步（從 Firestore 讀取最新狀態）
      if (window.AIMathAnalytics){
        window.AIMathAnalytics.track('stripe_checkout_return', { status: 'success', plan: plan });
      }
      _syncSubscriptionFromBackend();
      return { success: true, plan: plan };
    }

    if (checkout === 'cancel'){
      if (window.AIMathAnalytics){
        window.AIMathAnalytics.track('stripe_checkout_return', { status: 'cancel' });
      }
      return { success: false, cancelled: true };
    }

    return null;
  }

  /**
   * 從 Firestore 同步訂閱狀態到前端
   */
  function _syncSubscriptionFromBackend(){
    if (!window.AIMathFirebase || !window.AIMathFirebase.isConfigured()) return;
    var uid = getCurrentUID();
    if (!uid) return;

    var db = window.AIMathFirebase.getFirestore();
    if (!db) return;

    db.collection('subscriptions').doc(uid).get()
      .then(function(snap){
        if (!snap.exists) return;
        var data = snap.data();
        if (data && data.plan_status && window.AIMathSubscription){
          // Update local subscription state from server truth
          if (data.plan_status === 'paid_active'){
            window.AIMathSubscription.confirmPayment(data.plan_type, {
              context: 'stripe_webhook_sync',
              cta_source: 'stripe_webhook'
            });
          } else if (data.plan_status === 'trial'){
            window.AIMathSubscription.startTrial(data.plan_type, {
              context: 'stripe_webhook_sync',
              cta_source: 'stripe_webhook'
            });
          }
        }
      })
      .catch(function(e){
        console.warn('[Payment] Subscription sync failed:', e);
      });
  }

  /**
   * 監聽 Firestore 訂閱文件變更（即時同步）
   */
  function listenSubscriptionChanges(){
    if (!window.AIMathFirebase || !window.AIMathFirebase.isConfigured()) return null;
    var uid = getCurrentUID();
    if (!uid) return null;

    var db = window.AIMathFirebase.getFirestore();
    if (!db) return null;

    return db.collection('subscriptions').doc(uid).onSnapshot(function(snap){
      if (!snap.exists) return;
      var data = snap.data();
      if (data && data.plan_status && window.AIMathSubscription){
        var current = window.AIMathSubscription.getPlanStatus();
        if (current !== data.plan_status){
          // Server state changed — sync locally
          if (data.plan_status === 'paid_active'){
            window.AIMathSubscription.confirmPayment(data.plan_type, {
              context: 'firestore_realtime',
              cta_source: 'firestore_sync'
            });
          }
          // Reload UI
          if (typeof window._refreshPricingState === 'function'){
            window._refreshPricingState();
          }
        }
      }
    });
  }

  /**
   * 開始免費試用（不需 Stripe，直接本地 + Firestore）
   */
  function startFreeTrial(planType, meta){
    if (window.AIMathSubscription){
      window.AIMathSubscription.beginTrialCheckout(planType || 'standard', meta);
    }
    // Also sync to Firestore if available
    var uid = getCurrentUID();
    if (uid && window.AIMathFirebase && window.AIMathFirebase.isConfigured()){
      var db = window.AIMathFirebase.getFirestore();
      if (db){
        var sub = window.AIMathSubscription.getSubForCloud();
        db.collection('subscriptions').doc(uid).set({
          plan_type: sub.plan_type,
          plan_status: sub.plan_status,
          trial_start: sub.trial_start,
          expire_at: sub.expire_at,
          updated_at: new Date().toISOString()
        }, { merge: true }).catch(function(){});
      }
    }

    if (window.AIMathParentAuth && window.AIMathParentAuth.isLoggedIn()){
      window.AIMathParentAuth.syncSubscription(
        window.AIMathSubscription.getSubForCloud()
      );
    }

    return Promise.resolve();
  }

  /* ─── Export ─── */
  window.AIMathPayment = {
    isConfigured: isConfigured,
    startCheckout: startCheckout,
    startFreeTrial: startFreeTrial,
    handleCheckoutReturn: handleCheckoutReturn,
    listenSubscriptionChanges: listenSubscriptionChanges,
    getCurrentUID: getCurrentUID,
    PRICE_IDS: PRICE_IDS
  };
})();
