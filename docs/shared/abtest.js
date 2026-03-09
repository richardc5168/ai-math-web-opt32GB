/**
 * AIMathABTest — 前端 A/B 測試框架
 *
 * 儲存 key: aimath_abtest_v1
 * 支援多個同時進行的測試，每個測試有兩個變體 (A/B)。
 * 分配結果持久化到 localStorage，確保同一使用者始終看到同一變體。
 * 所有分配和轉換事件自動記錄到 AIMathAnalytics。
 */
(function(){
  'use strict';
  var KEY = 'aimath_abtest_v1';

  /* ─── 測試配置 ─── */
  var TESTS = {
    /* Test 1: Hero 標題文案 */
    hero_headline: {
      name: 'Hero 標題文案',
      variants: {
        A: { html: '台灣國小五六年級數學補弱<br>讓孩子每天願意做題', desc: '直述年級與補弱價值' },
        B: { html: '孩子不排斥做題<br>家長看得懂哪裡要補', desc: '更強調親子雙邊價值' }
      },
      active: true
    },
    /* Test 2: Hero CTA 文案 */
    hero_cta: {
      name: 'Hero CTA 文案',
      variants: {
        A: { label: '開始今日挑戰', desc: '原版文案' },
        B: { label: '免費試玩 — 不用註冊', desc: '強調免費+無門檻' }
      },
      active: true
    },
    /* Test 3: 免費版限制文案 */
    free_plan_message: {
      name: '免費版限制文案',
      variants: {
        A: { text: '不用註冊就能先試做，確認孩子願不願意做、AI 提示是否真的有幫助。', desc: '先強調低門檻' },
        B: { text: '免費版先用每天 10 題測試意願，升級後再看完整週報與補救建議。', desc: '先強調限制與升級差異' }
      },
      active: true
    },
    /* Test 4: Pricing 頁 Trial 按鈕顏色 */
    trial_btn_color: {
      name: '試用按鈕顏色',
      variants: {
        A: { color: '#238636', desc: '綠色（原版）' },
        B: { color: '#8957e5', desc: '紫色' }
      },
      active: true
    },
    /* Test 5: 痛點區塊顯示順序 */
    pain_order: {
      name: '痛點區塊順序',
      variants: {
        A: { order: 'default', desc: '放棄→弱點→補習→路徑' },
        B: { order: 'reversed', desc: '路徑→補習→弱點→放棄' }
      },
      active: true
    },
    /* Test 6: Star Pack CTA 位置 */
    star_pack_position: {
      name: '明星題組入口位置',
      variants: {
        A: { position: 'before-topics', desc: '主題精修上方（原版）' },
        B: { position: 'after-hero', desc: '緊接 Hero 下方' }
      },
      active: true
    },
    /* Test 7: 每日免費題數 */
    free_limit: {
      name: '免費每日題數',
      variants: {
        A: { limit: 10, desc: '10 題（原版）' },
        B: { limit: 15, desc: '15 題' }
      },
      active: true
    },
    /* Test 8: 題後升級提示 */
    post_question_upsell: {
      name: '題後升級提示',
      variants: {
        A: { title: '做得好！繼續保持', body: '升級後可以每天無限練習，解鎖 2,900+ 題完整題庫，搭配 AI 弱點分析更快進步。', primaryLabel: '查看升級方案' },
        B: { title: '今天已經有進步了', body: '如果想把今天卡住的題型一次補起來，升級後可直接看完整週報、明星題組與補救建議。', primaryLabel: '解鎖完整補救路線' }
      },
      active: true
    },
    /* Test 9: 家長週報 CTA 位置 */
    parent_report_cta_position: {
      name: '家長週報 CTA 位置',
      variants: {
        A: { position: 'after-summary', desc: '放在重點摘要後' },
        B: { position: 'after-ai-actions', desc: '放在 AI 補救建議後' }
      },
      active: true
    }
  };

  /* ─── 儲存 ─── */
  function load(){
    try {
      var raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : {};
    } catch(e){ return {}; }
  }

  function save(data){
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch(e){}
  }

  /* ─── 分配變體 ─── */
  function assign(testId){
    if (!TESTS[testId] || !TESTS[testId].active) return null;

    var data = load();
    if (data[testId]) return data[testId];

    // 50/50 隨機分配
    var variant = Math.random() < 0.5 ? 'A' : 'B';
    data[testId] = variant;
    save(data);

    // 記錄分配事件
    if (window.AIMathAnalytics){
      window.AIMathAnalytics.track('ab_assign', {
        test_id: testId,
        variant: variant,
        test_name: TESTS[testId].name
      });
    }

    return variant;
  }

  /* ─── 取得變體（不重新分配） ─── */
  function getVariant(testId){
    if (!TESTS[testId]) return null;
    var data = load();
    if (data[testId]) return data[testId];
    return assign(testId);
  }

  /* ─── 取得變體設定值 ─── */
  function getVariantConfig(testId){
    var variant = getVariant(testId);
    if (!variant || !TESTS[testId]) return null;
    return TESTS[testId].variants[variant] || null;
  }

  /* ─── 記錄轉換 ─── */
  function trackConversion(testId, action, data){
    var variant = getVariant(testId);
    if (!variant) return;

    if (window.AIMathAnalytics){
      window.AIMathAnalytics.track('ab_conversion', {
        test_id: testId,
        variant: variant,
        action: action || 'convert',
        test_name: TESTS[testId].name,
        data: data || {}
      });
    }
  }

  /* ─── 取得所有分配 ─── */
  function getAllAssignments(){
    var data = load();
    var result = {};
    Object.keys(TESTS).forEach(function(testId){
      if (TESTS[testId].active){
        result[testId] = {
          name: TESTS[testId].name,
          variant: data[testId] || null,
          config: data[testId] ? TESTS[testId].variants[data[testId]] : null
        };
      }
    });
    return result;
  }

  /* ─── 重設特定測試 ─── */
  function resetTest(testId){
    var data = load();
    delete data[testId];
    save(data);
  }

  /* ─── 重設所有測試 ─── */
  function resetAll(){
    try { localStorage.removeItem(KEY); } catch(e){}
  }

  /* ─── 取得測試列表 ─── */
  function getTests(){
    return JSON.parse(JSON.stringify(TESTS));
  }

  /* ─── Export ─── */
  window.AIMathABTest = {
    TESTS: TESTS,
    assign: assign,
    getVariant: getVariant,
    getVariantConfig: getVariantConfig,
    trackConversion: trackConversion,
    getAllAssignments: getAllAssignments,
    resetTest: resetTest,
    resetAll: resetAll,
    getTests: getTests
  };
})();
