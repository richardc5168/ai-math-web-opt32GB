# Monetization 8H Iteration Plan

更新日期：2026-03-09

目的：基於目前 ai-math-web 已存在的前端靜態站、local-first analytics、subscription mock flow、家長週報與星級題組架構，排出一個可連續執行 8 小時、每一階段完成後立即驗證並做乾淨 commit 的商業驗證節奏。

---

## 0. 核心判斷

這個 repo 現況不是「從零做 Monetization MVP」，而是：

1. 收費閉環、事件追蹤、明星題組、家長週報、A/B test 都已經有骨架。
2. 真正缺的是資料欄位一致性、跨頁狀態同步、家長價值敘事、明星場景與週報之間的回流鏈路。
3. 所以 8 小時迭代的主軸不應該是大改版，而應該是：
   - 補齊資料流
   - 收斂 CTA 與 gating
   - 強化 pack/report 的付費理由
   - 用最少變更建立可持續優化的節奏

四大聚焦主題：

- 收費閉環
- 留存與轉換數據
- 明星場景：分數 / 小數 / 百分率 / 生活應用題
- 家長週報 + 補救建議

---

## 1. 現有架構如何支撐這 4 件事

### 1.1 收費閉環

- 前端狀態機：`docs/shared/subscription.js`
- 定價頁：`docs/pricing/index.html`
- 免費限制：`docs/shared/daily_limit.js`
- 可重用升級入口：`docs/shared/upgrade_banner.js`, `docs/shared/completion_upsell.js`
- 既有家長與學生入口：`docs/index.html`, `docs/parent-report/index.html`, 各模組 `docs/*/index.html`
- 未來正式後端落點：`server.py`, `engine.py`, `app_identity.py`

判斷：

- 現況足夠驗證 `free -> trial -> checkout_pending -> paid_active -> expired`
- 8 小時內不應串正式金流，應優先把 source/context/event/status 一致化

### 1.2 留存與轉換數據

- 事件記錄：`docs/shared/analytics.js`
- 作答事件橋接：`docs/shared/attempt_telemetry.js`
- KPI 頁：`docs/kpi/index.html`
- 家長端與補救點擊：`docs/parent-report/index.html`
- A/B 實驗事件：`docs/shared/abtest.js`

判斷：

- 事件骨架已足夠，但還需要補齊統一欄位：`topic`, `grade`, `module_id`, `plan_type`, `plan_status`, `cta_source`
- 7 日 / 30 日留存與 report-to-return 目前仍屬弱點

### 1.3 明星場景

- 入口頁：`docs/star-pack/index.html`
- 分數：`docs/fraction-g5/`, `docs/fraction-word-g5/`, `docs/commercial-pack1-fraction-sprint/`
- 小數：`docs/interactive-decimal-g5/`, `docs/decimal-unit4/`
- 百分率：`docs/ratio-percent-g5/`
- 生活應用：`docs/life-applications-g5/`, `docs/interactive-g5-life-pack*-empire/`

判斷：

- 題組已存在，8 小時內應聚焦「入口、標籤、完成後摘要、升級理由」
- 不要在 8 小時內重造題庫或重構全部 pack metadata

### 1.4 家長週報 + 補救建議

- 前端報表：`docs/parent-report/index.html`
- 報表聚合：`learning/parent_report.py`
- 規則式推薦：`learning/remediation.py`
- 學習分析：`learning/analytics.py`

判斷：

- 後端聚合已可用，真正要補的是前端的「本週最弱三點 -> 直接去做哪三組題」
- 付費價值應聚焦在：看懂弱點、立即補救、下週有沒有變好

---

## 2. 八階段執行原則

每一階段都遵守以下規則：

1. 只改同一個商業目標下的檔案。
2. 不把 generated noise、bank 內容優化、文案改版混到同一個 commit。
3. 先做最小可行變更，再驗證，再 commit。
4. 若有改 `docs`，要同步 `dist_ai_math_web_pages/docs`。
5. 每一階段都寫下：變更摘要、影響檔案、驗收方式、下一步建議。

固定驗證命令：

```powershell
python tools/validate_all_elementary_banks.py
python scripts/verify_all.py
```

若該階段已 push 並等待 Pages 更新，再補：

```powershell
node tools/cross_validate_remote.cjs
```

---

## 3. 八階段 8 小時實作節奏

### 階段一：基線盤點凍結

目標：

- 確定本輪只聚焦 4 件事，不擴 scope
- 固定目前可重用的檔案與資料流

主要檔案：

- `MONETIZATION_MVP_AUDIT.md`
- `MVP_GAP_LIST.md`
- `ROADMAP_12_WEEKS.md`
- `MONETIZATION_8H_ITERATION_PLAN.md`

操作：

- 把現有功能、缺口、8 小時節奏寫清楚
- 列出這一輪不做的事：正式金流、重構所有 pack schema、全站視覺重做

驗收：

- 文件能回答「做什麼、先做什麼、驗證什麼、每階段 commit 什麼」

建議 commit：

- `docs: freeze monetization iteration baseline`

### 階段二：收費閉環收斂

目標：

- 讓 trial / checkout / expiry / gating 的資料流更一致

主要檔案：

- `docs/shared/subscription.js`
- `docs/pricing/index.html`
- `docs/shared/daily_limit.js`
- `docs/index.html`
- `docs/parent-report/index.html`

操作：

- 統一 plan status naming 與 CTA source naming
- 確保首頁、題後、家長週報、弱點區至少 4 個入口都能回到同一個 upgrade flow
- 補 `plan_type`, `plan_status`, `trial_start`, `paid_start`, `expire_at` 與 profile/cloud sync 對接欄位設計

驗收：

- 免費 / 標準 / 家庭版差異清楚
- 至少 3 個以上頁面能走到 upgrade flow
- 狀態切換一定有事件

建議 commit：

- `feat: tighten monetization subscription loop`

### 階段三：事件欄位正規化

目標：

- 把關鍵事件補到可做 funnel 與 retention 分析的程度

主要檔案：

- `docs/shared/analytics.js`
- `docs/shared/attempt_telemetry.js`
- `ANALYTICS_SCHEMA.md`
- `docs/kpi/index.html`

操作：

- 固定每個關鍵事件帶 `user_id`, `role`, `topic`, `grade`, `timestamp`, `session_id`
- 新增或補齊：`module_id`, `plan_type`, `plan_status`, `cta_source`
- 把 `question_start`, `retry_start`, `session_complete`, `return_next_day`, `return_next_week` 補到最小可用

驗收：

- 能查完整 funnel：`landing_page_view -> pricing_view -> trial_start -> checkout_start -> checkout_success`
- 能看主題維度與模組維度的作答行為

建議 commit：

- `feat: normalize monetization analytics fields`

### 階段四：明星場景成交入口

目標：

- 把 star pack 從「題組列表」提升成「付費主打入口」

主要檔案：

- `docs/star-pack/index.html`
- `STAR_PACK_SPEC.md`
- 必要時搭配對應模組 `docs/*/index.html`

操作：

- 收斂成會賣的 4 大主題包
- 每個 pack 清楚寫：適合誰、補什麼、做完能看到什麼結果
- 完成後事件要能標記：直接答對、看提示後答對、看提示仍錯、重做後答對

驗收：

- 首頁或任務區有清楚入口
- 學生能從 pack 頁進入完整練習
- 家長能從報表或 pack 結果看出價值

建議 commit：

- `feat: sharpen star pack conversion path`

### 階段五：家長週報轉成續訂理由

目標：

- 讓週報不是資訊展示，而是行動與續訂理由

主要檔案：

- `docs/parent-report/index.html`
- `learning/parent_report.py`
- `learning/remediation.py`
- `PARENT_REPORT_V2_SPEC.md`
- `RECOMMENDATION_ENGINE_V1.md`

操作：

- 固定 4 區：本週摘要、概念雷達、問題診斷、下週補救建議
- 強化 3 個最重要 CTA：先練哪三題型、AI 補救建議、直接進 pack/module
- 加入與上週比較的訊號

驗收：

- 家長一眼能看懂最弱概念
- 每個建議都能直接點入題組
- 完整週報維持付費 gating

建議 commit：

- `feat: strengthen parent report conversion loop`

### 階段六：首頁轉換導向收斂

目標：

- 讓首頁明確回答家長的五個問題：給誰、解什麼、孩子為何願意用、家長為何值得付費、免費與付費差在哪

主要檔案：

- `docs/index.html`
- `docs/shared/analytics.js`
- `docs/shared/subscription.js`

操作：

- 收斂 Hero、痛點、解法、明星場景、方案、FAQ
- 所有 CTA 都掛事件
- 不重做整站風格，只優化轉換敘事

驗收：

- Hero 主 CTA 與次 CTA 清楚
- 方案差異與家長價值能在首頁說清楚

建議 commit：

- `feat: refine landing conversion narrative`

### 階段七：A/B 測試位點收斂

目標：

- 把現有 A/B 框架集中在真正影響商業漏斗的位置

主要檔案：

- `docs/shared/abtest.js`
- `docs/kpi/index.html`
- `AB_TESTING_SPEC.md`
- `docs/index.html`
- `docs/pricing/index.html`
- `docs/parent-report/index.html`

操作：

- 先只保留 5 個實驗位點：Hero 標題、首頁主 CTA、免費版限制文案、題後升級提示、家長週報 CTA 位置
- 確保 variant assignment 與 `upgrade_click`, `trial_start`, `checkout_success` 能關聯

驗收：

- 每位 user 固定看到同一 variant
- KPI 頁可看 per-variant assignment / conversion

建議 commit：

- `feat: focus monetization ab experiments`

### 階段八：驗證、回顧、記錄結果

目標：

- 把這 8 小時的結果變成下一輪可以接續的 baseline

主要檔案：

- `METRICS_DASHBOARD.md`
- `TEST_PAYMENT_FLOW.md`
- `ROADMAP_12_WEEKS.md`
- `MONETIZATION_MVP_AUDIT.md`

操作：

- 記錄本輪哪些 funnel 改善了、哪些事件已可量測、哪些假設仍未被驗證
- 列出下一輪只做的 1-2 個重點，不把 scope 再放大

驗收：

- 文件能回答：本輪改了什麼、怎麼驗證、下一輪先做什麼
- 驗證命令全部通過

建議 commit：

- `docs: record monetization sprint outcomes`

---

## 4. 每階段固定驗證與 commit 模板

### 驗證清單

```powershell
python tools/validate_all_elementary_banks.py
python scripts/verify_all.py
```

若當前階段已 push：

```powershell
node tools/cross_validate_remote.cjs
```

### Commit 前檢查

1. 只 stage 本階段檔案。
2. 若動到 `docs/`，同步 `dist_ai_math_web_pages/docs/`。
3. 避免把 `data/generated/*`, `data/human_queue/*`, 自動優化輸出混進 commit。
4. 用單一訊息描述單一目標。

### 每階段收尾格式

- 變更摘要
- 影響檔案
- 驗收方式
- 下一步建議

---

## 5. 可直接貼給 Copilot 的主控 Prompt

```text
你現在是我的產品工程代理人，請以「先驗證商業，再擴產品」為最高原則，針對目前的 ai-GAME / ai-math-web 專案，執行一個 90 天變現驗證版本（Monetization Validation MVP）。

目標不是做完整教育平台，而是把現有產品收斂成：
1. 台灣國小五六年級
2. 數學補弱
3. 聚焦四大主題：分數、小數、百分率、生活應用題
4. 有免費試用、付費升級、家長週報、留存追蹤、弱點補救推薦

請嚴格遵守以下產品策略：
- 不新增大而全功能
- 不先做國中全課綱
- 不先做複雜社群功能
- 不先追求華麗動畫
- 先把「試用 -> 持續使用 -> 願意付費 -> 願意續訂」這條路徑打通
- 所有開發必須可量測
- 所有新功能都必須附帶追蹤事件與驗收條件
- 所有 UI 文案以「讓家長看得懂價值、讓學生願意持續做題」為準

技術要求：
- 盡量沿用現有架構
- 優先保持可離線、可靜態部署
- 如需支付可先做 mock mode，再保留未來串正式 payment provider 的介面
- 所有功能要可被後續 A/B test 擴充

執行方式：
- 只做當前階段最小可行變更
- 每完成一項，先驗證，再做乾淨 commit
- 輸出：變更摘要、影響檔案、驗收方式、下一步建議
```

---

## 6. 每日工作短模板

```text
今天只做一件事：完成 [功能名稱] 的最小可行版本。

請先：
1. 找出相關檔案
2. 說明目前實作狀態
3. 提出最小修改方案
4. 直接實作
5. 提供驗收步驟
6. 若有風險，列在最後

限制：
- 不做無關重構
- 不做過度設計
- 所有新功能都要掛事件追蹤
- 所有文案以家長看得懂為主
- 完成後先驗證再 commit
```

---

## 7. 最務實的第一段 Prompt

```text
請先掃描目前 ai-GAME / ai-math-web repo，產出一份 MONETIZATION_MVP_AUDIT.md。

目的：
我要在 90 天內驗證「台灣國小五六年級數學補弱」是否能形成付費訂閱。
請不要先亂改 UI，也不要做大功能，先盤點現況並列出：
1. 現有可重用功能
2. 商業閉環缺口
3. 留存追蹤缺口
4. 家長感知價值缺口
5. 建議的 P0 / P1 / P2 實作順序

請附：
- 涉及檔名
- 目前路由 / 資料流
- 風險說明
- 4 週 / 8 週 / 12 週路線圖

完成後先驗證，再 commit。
```
