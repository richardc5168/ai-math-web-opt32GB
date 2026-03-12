/**
 * auth_parent.js — 家長帳號系統
 *
 * 依賴：firebase_config.js（可選，未設定時降級為 localStorage）
 *
 * 功能：
 *   - Email / Password 註冊 + 登入（Firebase Auth）
 *   - 本機降級模式（無 Firebase 時用 localStorage）
 *   - 訂閱狀態綁定到 Firestore 帳號
 *   - 與 student_auth.js 整合（學生綁定到家長帳號下）
 */
(function(){
  'use strict';

  var LS_KEY = 'aimath_parent_auth_v1';
  var _currentUser = null;
  var _profile = null;
  var _listeners = [];

  /* ─── Helpers ─── */
  function nowIso(){ return new Date().toISOString(); }
  function safeJson(s, fb){ try { return JSON.parse(s); } catch(e){ return fb; } }

  function _firebaseAvailable(){
    return !!(window.AIMathFirebase && window.AIMathFirebase.isConfigured() && window.AIMathFirebase.getAuth());
  }

  function _notify(event, data){
    _listeners.forEach(function(fn){ try { fn(event, data); } catch(e){} });
  }

  /* ─── Firestore profile helpers ─── */
  function _firestoreProfileRef(uid){
    var db = window.AIMathFirebase.getFirestore();
    if (!db) return null;
    return db.collection('parents').doc(uid);
  }

  function _loadFirestoreProfile(uid){
    var ref = _firestoreProfileRef(uid);
    if (!ref) return Promise.resolve(null);
    return ref.get().then(function(snap){
      return snap.exists ? snap.data() : null;
    }).catch(function(){ return null; });
  }

  function _saveFirestoreProfile(uid, data){
    var ref = _firestoreProfileRef(uid);
    if (!ref) return Promise.resolve();
    return ref.set(data, { merge: true }).catch(function(e){
      console.warn('[ParentAuth] Firestore save failed', e);
    });
  }

  /* ─── localStorage fallback ─── */
  function _loadLocal(){
    return safeJson(localStorage.getItem(LS_KEY), null);
  }

  function _saveLocal(profile){
    try { localStorage.setItem(LS_KEY, JSON.stringify(profile)); } catch(e){}
  }

  /* ─── Default profile ─── */
  function _defaultProfile(uid, email){
    return {
      uid: uid,
      email: email,
      display_name: '',
      children: [],            // [{ name, pin }]
      subscription: null,      // synced from subscription.js
      created_at: nowIso(),
      updated_at: nowIso()
    };
  }

  /* ─── Core Auth Functions ─── */

  /**
   * 註冊家長帳號
   * @param {string} email
   * @param {string} password — 至少 6 碼
   * @returns {Promise<{uid, email, profile}>}
   */
  function register(email, password){
    if (!email || !password) return Promise.reject(new Error('請輸入 Email 和密碼'));
    if (password.length < 6) return Promise.reject(new Error('密碼至少 6 碼'));

    if (_firebaseAvailable()){
      var auth = window.AIMathFirebase.getAuth();
      return auth.createUserWithEmailAndPassword(email, password)
        .then(function(cred){
          _currentUser = cred.user;
          var profile = _defaultProfile(cred.user.uid, email);
          _profile = profile;
          _saveLocal(profile);
          return _saveFirestoreProfile(cred.user.uid, profile).then(function(){
            _notify('register', { uid: cred.user.uid, email: email });
            return { uid: cred.user.uid, email: email, profile: profile };
          });
        });
    }

    // Offline fallback
    var uid = 'local_' + Date.now();
    var profile = _defaultProfile(uid, email);
    profile.password_hash = _simpleHash(password); // local only, not real security
    _profile = profile;
    _currentUser = { uid: uid, email: email };
    _saveLocal(profile);
    _notify('register', { uid: uid, email: email });
    return Promise.resolve({ uid: uid, email: email, profile: profile });
  }

  /**
   * 登入
   */
  function login(email, password){
    if (!email || !password) return Promise.reject(new Error('請輸入 Email 和密碼'));

    if (_firebaseAvailable()){
      var auth = window.AIMathFirebase.getAuth();
      return auth.signInWithEmailAndPassword(email, password)
        .then(function(cred){
          _currentUser = cred.user;
          return _loadFirestoreProfile(cred.user.uid).then(function(profile){
            if (!profile) profile = _defaultProfile(cred.user.uid, email);
            _profile = profile;
            _saveLocal(profile);
            _notify('login', { uid: cred.user.uid, email: email });
            return { uid: cred.user.uid, email: email, profile: profile };
          });
        });
    }

    // Offline fallback
    var stored = _loadLocal();
    if (!stored || stored.email !== email){
      return Promise.reject(new Error('帳號不存在'));
    }
    if (stored.password_hash !== _simpleHash(password)){
      return Promise.reject(new Error('密碼錯誤'));
    }
    _currentUser = { uid: stored.uid, email: email };
    _profile = stored;
    _notify('login', { uid: stored.uid, email: email });
    return Promise.resolve({ uid: stored.uid, email: email, profile: stored });
  }

  /**
   * 登出
   */
  function logout(){
    if (_firebaseAvailable()){
      var auth = window.AIMathFirebase.getAuth();
      auth.signOut().catch(function(){});
    }
    _currentUser = null;
    _profile = null;
    try { localStorage.removeItem(LS_KEY); } catch(e){}
    _notify('logout', {});
    return Promise.resolve();
  }

  /**
   * 重設密碼
   */
  function resetPassword(email){
    if (!email) return Promise.reject(new Error('請輸入 Email'));
    if (_firebaseAvailable()){
      return window.AIMathFirebase.getAuth().sendPasswordResetEmail(email);
    }
    return Promise.reject(new Error('離線模式不支援密碼重設'));
  }

  /* ─── State Query ─── */
  function isLoggedIn(){
    return !!_currentUser;
  }

  function getUser(){
    return _currentUser ? { uid: _currentUser.uid, email: _currentUser.email } : null;
  }

  function getProfile(){
    return _profile;
  }

  /* ─── Profile Management ─── */
  function updateProfile(patch){
    if (!_profile) return Promise.reject(new Error('尚未登入'));
    Object.assign(_profile, patch, { updated_at: nowIso() });
    _saveLocal(_profile);
    if (_firebaseAvailable() && _currentUser){
      return _saveFirestoreProfile(_currentUser.uid, _profile);
    }
    return Promise.resolve(_profile);
  }

  /**
   * 綁定學生到家長帳號
   */
  function addChild(name, pin){
    if (!_profile) return Promise.reject(new Error('請先登入家長帳號'));
    if (!name) return Promise.reject(new Error('請輸入學生暱稱'));
    var children = _profile.children || [];
    var existing = children.find(function(c){ return c.name === name; });
    if (existing) return Promise.reject(new Error('此學生暱稱已存在'));
    children.push({
      name: String(name).trim(),
      pin: String(pin || '').trim() || '0000',
      added_at: nowIso()
    });
    return updateProfile({ children: children });
  }

  /**
   * 同步訂閱狀態到家長帳號
   */
  function syncSubscription(subData){
    if (!_profile) return;
    return updateProfile({ subscription: subData });
  }

  /* ─── Event Listeners ─── */
  function onChange(fn){
    _listeners.push(fn);
  }

  /* ─── Firebase Auth State Observer ─── */
  function _initAuthObserver(){
    if (!_firebaseAvailable()) return;
    var auth = window.AIMathFirebase.getAuth();
    auth.onAuthStateChanged(function(user){
      if (user){
        _currentUser = user;
        _loadFirestoreProfile(user.uid).then(function(profile){
          if (profile){
            _profile = profile;
            _saveLocal(profile);
          } else {
            // First time — check localStorage
            var local = _loadLocal();
            if (local && local.uid === user.uid){
              _profile = local;
            } else {
              _profile = _defaultProfile(user.uid, user.email);
            }
            _saveFirestoreProfile(user.uid, _profile);
          }
          _notify('auth_state', { uid: user.uid, email: user.email, loggedIn: true });
        });
      } else {
        // Check localStorage for offline session
        var local = _loadLocal();
        if (local && local.uid && local.uid.startsWith('local_')){
          _currentUser = { uid: local.uid, email: local.email };
          _profile = local;
          _notify('auth_state', { uid: local.uid, email: local.email, loggedIn: true });
        } else {
          _currentUser = null;
          _profile = null;
          _notify('auth_state', { loggedIn: false });
        }
      }
    });
  }

  /* ─── Offline password hash (NOT cryptographic — for local demo only) ─── */
  function _simpleHash(str){
    var hash = 0;
    for (var i = 0; i < str.length; i++){
      var c = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + c;
      hash |= 0;
    }
    return 'h_' + Math.abs(hash).toString(36);
  }

  /* ─── Login UI Builder ─── */
  function buildLoginModalHTML(){
    return '<div id="parentAuthModal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:10000;background:rgba(0,0,0,.75);align-items:center;justify-content:center;">'
      + '<div style="background:#161b22;border:1px solid #30363d;border-radius:16px;padding:32px;max-width:400px;width:90%;position:relative;">'
      + '<button onclick="document.getElementById(\'parentAuthModal\').style.display=\'none\'" style="position:absolute;top:12px;right:12px;background:none;border:none;color:#8b949e;font-size:1.2rem;cursor:pointer;">&times;</button>'
      + '<h3 style="color:#fff;margin:0 0 4px;font-size:1.2rem;">👨‍👩‍👧 家長帳號</h3>'
      + '<p style="color:#8b949e;font-size:.85rem;margin:0 0 20px;">登入後訂閱狀態跨裝置同步</p>'
      + '<div id="parentAuthMsg" style="display:none;padding:8px 12px;border-radius:8px;font-size:.85rem;margin-bottom:12px;"></div>'
      + '<div id="parentAuthForm">'
      + '<input id="parentEmail" type="email" placeholder="Email" style="width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;font-size:.95rem;margin-bottom:10px;box-sizing:border-box;">'
      + '<input id="parentPassword" type="password" placeholder="密碼（至少 6 碼）" style="width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;font-size:.95rem;margin-bottom:16px;box-sizing:border-box;">'
      + '<div style="display:flex;gap:10px;">'
      + '<button onclick="AIMathParentAuth._uiLogin()" style="flex:1;background:#238636;color:#fff;border:none;padding:10px;border-radius:8px;font-weight:700;cursor:pointer;">登入</button>'
      + '<button onclick="AIMathParentAuth._uiRegister()" style="flex:1;background:#1f6feb;color:#fff;border:none;padding:10px;border-radius:8px;font-weight:700;cursor:pointer;">註冊</button>'
      + '</div>'
      + '<div style="text-align:center;margin-top:10px;">'
      + '<a href="#" onclick="AIMathParentAuth._uiReset();return false;" style="color:#58a6ff;font-size:.82rem;">忘記密碼？</a>'
      + '</div>'
      + '</div>'
      + '<div id="parentAuthLoggedIn" style="display:none;text-align:center;">'
      + '<div style="font-size:2rem;margin-bottom:8px;">✅</div>'
      + '<div id="parentAuthUserInfo" style="color:#c9d1d9;font-size:.95rem;margin-bottom:16px;"></div>'
      + '<button onclick="AIMathParentAuth._uiLogout()" style="background:#30363d;color:#c9d1d9;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;">登出</button>'
      + '</div>'
      + '</div>'
      + '</div>';
  }

  function _showMsg(text, isError){
    var el = document.getElementById('parentAuthMsg');
    if (!el) return;
    el.style.display = 'block';
    el.style.background = isError ? 'rgba(248,81,73,.15)' : 'rgba(63,185,80,.15)';
    el.style.color = isError ? '#f85149' : '#3fb950';
    el.textContent = text;
  }

  function _updateModalUI(){
    var form = document.getElementById('parentAuthForm');
    var loggedIn = document.getElementById('parentAuthLoggedIn');
    var userInfo = document.getElementById('parentAuthUserInfo');
    if (!form || !loggedIn) return;
    if (isLoggedIn()){
      form.style.display = 'none';
      loggedIn.style.display = 'block';
      if (userInfo) userInfo.textContent = '已登入：' + (_currentUser.email || '');
    } else {
      form.style.display = 'block';
      loggedIn.style.display = 'none';
    }
  }

  function _uiLogin(){
    var email = (document.getElementById('parentEmail') || {}).value;
    var pw = (document.getElementById('parentPassword') || {}).value;
    login(email, pw).then(function(){
      _showMsg('登入成功！', false);
      _updateModalUI();
    }).catch(function(e){
      _showMsg(e.message || '登入失敗', true);
    });
  }

  function _uiRegister(){
    var email = (document.getElementById('parentEmail') || {}).value;
    var pw = (document.getElementById('parentPassword') || {}).value;
    register(email, pw).then(function(){
      _showMsg('註冊成功！', false);
      _updateModalUI();
    }).catch(function(e){
      _showMsg(e.message || '註冊失敗', true);
    });
  }

  function _uiLogout(){
    logout().then(function(){
      _updateModalUI();
      _showMsg('已登出', false);
    });
  }

  function _uiReset(){
    var email = (document.getElementById('parentEmail') || {}).value;
    resetPassword(email).then(function(){
      _showMsg('重設密碼郵件已發送，請查看信箱', false);
    }).catch(function(e){
      _showMsg(e.message || '無法發送重設郵件', true);
    });
  }

  function showLoginModal(){
    var modal = document.getElementById('parentAuthModal');
    if (!modal){
      // Inject modal if not yet in DOM
      var div = document.createElement('div');
      div.innerHTML = buildLoginModalHTML();
      document.body.appendChild(div.firstChild);
      modal = document.getElementById('parentAuthModal');
    }
    _updateModalUI();
    modal.style.display = 'flex';
  }

  /* ─── Build nav login button HTML ─── */
  function buildNavButtonHTML(){
    if (isLoggedIn()){
      return '<button onclick="AIMathParentAuth.showLoginModal()" style="background:none;border:1px solid #3fb950;color:#3fb950;padding:4px 14px;border-radius:6px;font-size:.82rem;cursor:pointer;font-weight:600;">👨‍👩‍👧 '
        + (_currentUser.email || '').split('@')[0]
        + '</button>';
    }
    return '<button onclick="AIMathParentAuth.showLoginModal()" style="background:none;border:1px solid #58a6ff;color:#58a6ff;padding:4px 14px;border-radius:6px;font-size:.82rem;cursor:pointer;font-weight:600;">🔑 家長登入</button>';
  }

  /* ─── Init ─── */
  function _init(){
    // Restore from localStorage
    var local = _loadLocal();
    if (local && local.uid){
      _currentUser = { uid: local.uid, email: local.email };
      _profile = local;
    }
    // Set up Firebase observer when ready
    if (window.AIMathFirebase){
      window.AIMathFirebase.onReady(function(){
        _initAuthObserver();
      });
    }
  }

  _init();

  /* ─── Export ─── */
  window.AIMathParentAuth = {
    register: register,
    login: login,
    logout: logout,
    resetPassword: resetPassword,
    isLoggedIn: isLoggedIn,
    getUser: getUser,
    getProfile: getProfile,
    updateProfile: updateProfile,
    addChild: addChild,
    syncSubscription: syncSubscription,
    onChange: onChange,
    showLoginModal: showLoginModal,
    buildLoginModalHTML: buildLoginModalHTML,
    buildNavButtonHTML: buildNavButtonHTML,
    _uiLogin: _uiLogin,
    _uiRegister: _uiRegister,
    _uiLogout: _uiLogout,
    _uiReset: _uiReset
  };
})();
