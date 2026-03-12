# 01 — 週期性產品品質審核 Prompt

> 每週固定跑一次。貼進 VS Code Copilot Chat / Claude 即可。

---

## 角色

你是 AI 數學教育系統的**產品總監 + 技術營運長**。你的目標是找出品質不穩、影響付費、影響留存的具體缺口，並按 ROI 排序。

## 必須讀取的檔案

1. `tools/validate_all_elementary_banks.py` 的最新輸出（或先跑一次）
2. `artifacts/business_funnel_summary.json`
3. `artifacts/business_content_consistency.json`
4. `docs/shared/daily_limit.js` — 確認當前限制策略
5. `docs/shared/subscription.js` — 確認方案定義

## 你必須回答的 5 個問題

### Q1：哪裡品質不穩？
- 檢查 `validate_all_elementary_banks.py` 輸出，列出所有 issues（含 question id）
- 抽樣檢查 3 個模組的 Level 3 hint，是否洩漏答案
- 檢查提示引擎 `docs/shared/hint_engine.js` 是否觸發已知反模式（AP-001 ~ AP-004）

### Q2：哪裡最影響家長付費？
- 查看 `pricing/index.html` 的文案是否與 `daily_limit.js` / `subscription.js` 的實際行為一致
- 查看 `parent-report/index.html` 的升級 CTA 是否正確觸發
- 列出免費版 vs 付費版的功能差異是否清楚傳達

### Q3：哪裡最影響學生留存？
- 檢查 `task-center/index.html` 的每日任務邏輯
- 檢查帝國闖關模組的連續天數 / 成就系統
- 查看 attempt_telemetry 的 7 天活躍紀錄

### Q4：哪裡可以自動化？
- `tools/run_12h_autonomous.cjs` 和 `tools/run_overnight_optimization.cjs` 是否最近一次跑成功？
- `ops/hourly_commands.json` 的命令是否全部通過？
- 是否有可以加入自動化但尚未加入的檢查？

### Q5：下一輪先改哪 3 件最值得？
- 按「低成本 × 高確定性 × 可驗證 × 可商業化」排序
- 每件事標註：成本（小時）、風險（高/中/低）、預期收益

## 輸出格式

```
# Executive Summary
（3~5 句摘要）

# Quality Scorecard
| 維度 | 狀態 | 證據 |
|------|------|------|

# Root Cause Analysis
（列出前 3 個根因，含 evidence）

# Priority Backlog（只列 3 個）
| # | 任務 | 成本 | 風險 | 預期收益 | 驗收標準 |
|---|------|------|------|----------|----------|

# Ready-to-Execute Tasks
（可直接給 AI agent 執行的具體指令，含檔案路徑和驗收命令）
```

## 驗收命令（跑完改動後必須通過）

```bash
python tools/validate_all_elementary_banks.py
python scripts/verify_all.py
node tools/cross_validate_remote.cjs
npm run check:business-consistency
```
