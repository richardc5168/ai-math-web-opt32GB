# TEST PAYMENT FLOW

## Scope

This document verifies the current mock subscription lifecycle for the static deployment path.

Supported states:

- `free`
- `checkout_pending`
- `trial`
- `paid_active`
- `expired`

Primary UI entry:

- `docs/pricing/index.html`

Shared logic:

- `docs/shared/subscription.js`
- `docs/shared/student_auth.js`
- `docs/shared/daily_limit.js`

## Expected Data Fields

The active student profile and subscription state should carry:

- `plan_type`
- `plan_status`
- `trial_start`
- `paid_start`
- `expire_at`

## Normal Trial Flow

1. Open the pricing page.
2. Confirm the current status card shows `免費版` / `free`.
3. Click `免費試用 7 天` on either `標準版` or `家庭版`.
4. Confirm the modal opens and the plan details are correct.
5. Click `立即開始試用`.

Expected result:

- subscription state becomes `trial`
- `trial_start` and `expire_at` are populated
- status banner shows remaining trial days
- `trial_start` and `subscription_status_change` events are recorded
- full report and star-pack gating read as unlocked

## Direct Paid Activation Flow

1. Open the pricing modal for a paid plan.
2. Click `模擬直接開通`.

Expected result:

- state transitions through `checkout_pending` into `paid_active`
- `paid_start` and `expire_at` are populated
- banner shows the paid validity date
- `checkout_start`, `checkout_success`, and `subscription_status_change` are recorded

## Pending Checkout Flow

1. Use the pricing page status card.
2. Choose a plan in the mock plan selector.
3. Click `建立待結帳`.

Expected result:

- state becomes `checkout_pending`
- banner shows `待結帳`
- `checkout_start` and `subscription_status_change` are recorded
- no paid-only unlock should be assumed until trial or paid activation follows

## Trial Expiry Flow

1. Start a trial.
2. Use the pricing status card and click `標記到期`.

Expected result:

- state becomes `expired`
- banner shows `已到期`
- paid-only surfaces become gated again
- `subscription_force_expire` and `subscription_status_change` are recorded

## Cancel / Expired Flow

1. Start a paid or trial state.
2. Trigger `AIMathSubscription.cancelSubscription(...)` from a dev console or future account page.

Expected result:

- state becomes `expired`
- the same feature gating as an expired trial applies
- `subscription_cancel` and `subscription_status_change` are recorded

## Reset To Free

1. Use the pricing status card.
2. Click `回到免費`.

Expected result:

- state becomes `free`
- `trial_start`, `paid_start`, and `expire_at` clear out
- free limits apply again
- `subscription_reset` and `subscription_status_change` are recorded

## Feature Gating Checks

Check these after each state change:

1. `AIMathSubscription.getDailyLimit()`
2. `AIMathSubscription.canAccessFullReport()`
3. `AIMathSubscription.canAccessStarPack()`
4. daily limit upgrade prompt on empire-style modules
5. parent report upgrade CTA / gating

Expected gating:

- `free`: daily limit enforced, full report locked, star pack locked
- `trial`: unlimited questions, full report unlocked, star pack unlocked
- `paid_active`: same unlock as trial, but paid banner/date shown
- `expired`: same restrictions as free

## Analytics Checks

Inspect local analytics storage or KPI pages and confirm these events appear when relevant:

- `upgrade_click`
- `checkout_start`
- `trial_start`
- `checkout_success`
- `subscription_status_change`
- `subscription_expired` or `subscription_force_expire`
- `subscription_cancel`
- `subscription_reset`

## Replacement Path For Real Provider

When a real payment provider is added later, keep these stable entry points:

- `startCheckout(plan, meta)`
- `beginTrialCheckout(plan, meta)`
- `activatePaidPlan(plan, meta)`

The UI should keep calling shared subscription helpers while the underlying implementation swaps from mock state transitions to provider callbacks or server reconciliation.# TEST_PAYMENT_FLOW.md — Mock 付費流程測試

## 前置條件
- 開啟 Chrome DevTools Console
- 前往任一練習頁面

## 測試 1：正常免費流程
1. 清除 localStorage：`localStorage.removeItem('aimath_subscription_v1')`
2. 重新整理頁面
3. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "free"`
4. 做 10 題後 → 出現每日限制提示
5. 限制提示有「免費試用 7 天」和「查看方案」按鈕

## 測試 2：開始試用
1. 前往 /pricing/
2. 點擊標準版「🎁 免費試用 7 天」
3. 在彈出視窗點「✅ 立即開始試用」
4. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "trial", plan_type: "standard"`
5. 回到練習頁面 → 每日限制不再出現
6. 驗證事件：`AIMathAnalytics.query({event:'trial_start'})` → 有 1 筆

## 測試 3：模擬付款成功
1. Console 執行：`AIMathSubscription.confirmPayment('standard')`
2. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "paid_active"`
3. 驗證事件：`AIMathAnalytics.query({event:'checkout_success'})` → 有 1 筆

## 測試 4：模擬試用到期
1. Console 手動設定過期時間：
   ```js
   var sub = JSON.parse(localStorage.getItem('aimath_subscription_v1'));
   sub.expire_at = new Date(Date.now() - 1000).toISOString();
   localStorage.setItem('aimath_subscription_v1', JSON.stringify(sub));
   ```
2. 重新整理頁面
3. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "expired"`
4. 每日限制重新出現

## 測試 5：取消訂閱
1. Console: `AIMathSubscription.cancelSubscription()`
2. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "expired"`

## 測試 6：重設為免費
1. Console: `AIMathSubscription.resetToFree()`
2. 驗證：`AIMathSubscription.getPlanInfo()` → `plan_status: "free", plan_type: "free"`

## 測試 7：權限切換驗證
| 狀態 | `isPaid()` | `canAccessStarPack()` | `getDailyLimit()` | `canAccessFullReport()` |
|------|-----------|----------------------|-------------------|------------------------|
| free | false | false | 10 | false |
| trial | true | true | -1 | true |
| paid_active | true | true | -1 | true |
| expired | false | false | 10 | false |

## 測試 8：升級入口驗證
從以下頁面可進入升級流程：
1. **首頁** → pricing 方案區連結
2. **pricing 頁** → 方案卡片 CTA 按鈕
3. **每日限制對話框** → 「免費試用 7 天」按鈕
4. **升級 Banner** → 底部固定 banner
5. **家長週報** → 報告底部升級 CTA

## 未來 Stripe 整合
替換 `confirmPayment()` 為 Stripe Checkout webhook callback。
subscription.js 的 `mock_mode: true` 改為 false 後串接真實 API。
