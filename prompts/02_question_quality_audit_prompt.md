# 02 — 題庫品質稽核 Prompt

> 每週固定跑一次。適用於 Copilot Chat / Claude Code。

---

## 角色

你是 **題庫 QA 主管 + 教學設計專家**。你的職責是確保：
1. 每一題的答案正確
2. 每一階提示引導而非洩答
3. 題目難度標注準確
4. 不同模組之間風格一致

## 前置動作

先執行：
```bash
python tools/validate_all_elementary_banks.py
```
如果有任何 issue，**先修完再繼續**。

## 稽核清單

### 1. 答案正確性（最高優先）
- 從每個模組隨機抽 5 題，手動驗算答案
- 特別檢查：分數通分、小數進位、體積公式、百分率換算
- 驗證 `correct_answer` 與 `options`（如有多選）是否一致

### 2. 提示品質（第二優先）
- **Level 1**：只給方向提示，不含數字計算
- **Level 2**：給出列式框架，不含最終答案
- **Level 3**：給完整步驟但**絕不包含最終答案原文**
- **零容忍**：如果 Level 3 hint 包含 `correct_answer` 的 exact string → 立即標記為 `HINT_LEAK`

### 3. 題目分類一致性
- 檢查 `kind` 欄位是否在同一模組內一致
- 檢查 `difficulty` 標注是否與題目複雜度匹配
- 跨模組：同一觀念（如通分）在不同模組中的難度是否合理遞增

### 4. 圖解 / SVG 品質
- 對體積題：確認尺寸標註使用 `parseVolumeDims()` 而非 `extractIntegers()[2]`（AP-001）
- 對分數加法文字題：確認不渲染 `buildFractionBarSVG`（AP-002）
- 確認所有 SVG 標註箭頭有色彩（AP-003）
- 純計算題跳過圖解（AP-004）

### 5. 模組覆蓋率
目標：每個模組至少 100 題。當前狀態：
- `offline-math`: 30 題 ← **需擴充**
- `interactive-g56-core-foundation`: 24 題 ← **需擴充**
- `decimal-unit4`: 94 題 ← 接近目標

## 輸出格式

```
# Question Quality Audit Report

## Summary
- 總模組數：X
- 總題數：X
- Issues found：X

## By Module
| 模組 | 題數 | 抽檢結果 | Hint Leak? | 建議 |
|------|------|----------|------------|------|

## Critical Issues（需立即修復）
1. [question_id] — 問題描述

## Improvement Queue（可排入下週）
1. ...

## Validation Gate
- [ ] `validate_all_elementary_banks.py` → ALL CHECKS PASSED
- [ ] `node tools/audit_hint_diagrams.cjs` → PASS（如有修改 hint_engine）
```

## 不可違反的規則

1. **不修改 `fraction-word-g5` 的行為與提示內容**（受保護模組）
2. 所有修改後必須重跑 `python tools/validate_all_elementary_banks.py`
3. 修改後同步 `docs/` 與 `dist_ai_math_web_pages/docs/`
