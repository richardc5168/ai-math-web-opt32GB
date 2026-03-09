# AB Testing Spec

目的：在不引入重型平台的前提下，驗證哪些文案與入口位置更能帶動升級。

## 1. 實作位置

- 設定檔：`docs/shared/abtest.js`
- 套用頁面：`docs/index.html`, `docs/pricing/index.html`, `docs/parent-report/index.html`
- 題後提示：`docs/shared/completion_upsell.js`
- 統計頁面：`docs/kpi/index.html`

## 2. 儲存方式

- localStorage key：`aimath_abtest_v1`
- 每位使用者固定看到同一 variant

## 3. 目前測試項目

| test_id | 內容 | A | B |
|---------|------|---|---|
| `hero_headline` | Hero 標題文案 | 台灣國小五六年級數學補弱 | 孩子不排斥做題 / 家長看得懂要補什麼 |
| `hero_cta` | Hero CTA 文案 | 開始今日挑戰 | 免費試玩 — 不用註冊 |
| `free_plan_message` | 免費版限制文案 | 強調先低門檻試用 | 強調免費限制與升級差異 |
| `trial_btn_color` | 試用按鈕顏色 | 綠色 | 紫色 |
| `pain_order` | 痛點區塊順序 | default | reversed |
| `star_pack_position` | 明星題組入口位置 | before-topics | after-hero |
| `free_limit` | 每日免費題數 | 10 | 15 |
| `post_question_upsell` | 題後升級提示 | 強調無限練習 | 強調完整補救路線 |
| `parent_report_cta_position` | 家長週報 CTA 位置 | 重點摘要後 | AI 補救建議後 |

## 4. 事件關聯

### 分配事件

- `ab_assign`
- data：`test_id`, `variant`, `test_name`

### 轉換事件

- `ab_conversion`
- data：`test_id`, `variant`, `action`, `test_name`

建議主要關聯以下商業事件：

- `upgrade_click`
- `trial_start`
- `checkout_success`
- 題後 upsell 主按鈕 / 次按鈕點擊
- 家長週報升級提示點擊

## 5. 目前能力

- 支援 config 切換 active / inactive
- 自動 50/50 assignment
- 支援 reset 單一測試或全部測試
- KPI 頁面可看 per-variant assignment / conversion / rate

## 6. 最小實作原則

- 不做外部實驗平台整合
- 不做過度抽象的 targeting engine
- 先證明哪些文字和入口更有效，再決定是否升級基礎設施

## 7. Acceptance Criteria

- 可在 config 中調整測試開關
- 可記錄使用者看到哪個 variant
- 可比較 variant 的升級相關差異
- 不需改動核心流程即可擴充下一個測試
