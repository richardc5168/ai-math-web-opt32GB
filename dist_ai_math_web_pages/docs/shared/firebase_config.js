/**
 * firebase_config.js — Firebase 初始化設定
 *
 * 使用方式：
 *   1. 在 Firebase Console 建立專案 → 啟用 Auth + Firestore
 *   2. 把 firebaseConfig 填入下方
 *   3. 部署後在 Firebase Console 啟用 Email/Password 登入
 *
 * SDK: Firebase 10.x compat (CDN, 適合靜態站)
 */
(function(){
  'use strict';

  /* ─── Firebase Project Config ─── */
  /* 請將下方替換成你的 Firebase 專案金鑰 */
  var firebaseConfig = {
    apiKey:            '', // ← Firebase Console → Project Settings → Web App
    authDomain:        '', // ← your-project.firebaseapp.com
    projectId:         '', // ← your-project-id
    storageBucket:     '', // ← your-project.appspot.com
    messagingSenderId: '', // ← from Firebase Console
    appId:             ''  // ← from Firebase Console
  };

  /* ─── SDK Loader ─── */
  var SDK_VERSION = '10.12.2';
  var CDN_BASE = 'https://www.gstatic.com/firebasejs/' + SDK_VERSION;
  var _ready = false;
  var _readyCallbacks = [];

  function isConfigured(){
    return !!(firebaseConfig.apiKey && firebaseConfig.projectId);
  }

  function onReady(fn){
    if (_ready) { fn(); return; }
    _readyCallbacks.push(fn);
  }

  function _notifyReady(){
    _ready = true;
    _readyCallbacks.forEach(function(fn){ try { fn(); } catch(e){} });
    _readyCallbacks = [];
  }

  function loadScript(src){
    return new Promise(function(resolve, reject){
      var s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function init(){
    if (!isConfigured()){
      console.warn('[Firebase] Config not set — running in offline/mock mode');
      _notifyReady();
      return;
    }
    if (window.firebase && window.firebase.apps && window.firebase.apps.length > 0){
      _notifyReady();
      return;
    }
    Promise.all([
      loadScript(CDN_BASE + '/firebase-app-compat.js'),
      loadScript(CDN_BASE + '/firebase-auth-compat.js'),
      loadScript(CDN_BASE + '/firebase-firestore-compat.js')
    ]).then(function(){
      window.firebase.initializeApp(firebaseConfig);
      console.log('[Firebase] Initialized');
      _notifyReady();
    }).catch(function(err){
      console.error('[Firebase] SDK load failed, falling back to offline mode', err);
      _notifyReady();
    });
  }

  /* ─── Public API ─── */
  window.AIMathFirebase = {
    isConfigured: isConfigured,
    onReady: onReady,
    getAuth: function(){ return window.firebase && window.firebase.auth ? window.firebase.auth() : null; },
    getFirestore: function(){ return window.firebase && window.firebase.firestore ? window.firebase.firestore() : null; },
    init: init
  };

  // Auto-init on DOM ready
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
