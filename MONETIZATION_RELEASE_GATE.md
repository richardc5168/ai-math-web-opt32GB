# Monetization Release Gate

> Updated: 2026-03-10

目的：把 Monetization Validation MVP 的第 1 到第 8 階段收斂成可發版、可驗證、可持續 8 小時優化的最小 gate。

## 1. Stage Status

| Stage | Focus | Status | Commit |
|------|------|--------|--------|
| 1 | Repo audit / gap mapping | done | 既有 audit 文件 |
| 2 | 收費閉環 | done | `376f3801d` |
| 3 | 事件追蹤與 KPI | done | `c79dcf27a` |
| 4 | 明星場景轉換入口 | done | `72b9478f8` |
| 5 | 家長週報轉換強化 | done | `eec854fd6` |
| 6 | Landing page 轉換敘事 | done | `dd93ea464` |
| 7 | A/B test coverage | done | `a787cbba5` |
| 8 | Release gate + autonomous reviewer | done | this stage |

## 2. Release Gate

每次進入發版前，至少確認以下 4 項：

1. `docs` 與 `dist_ai_math_web_pages/docs` 同步。
2. `tools/validate_all_elementary_banks.py` 必須全綠。
3. `scripts/verify_all.py` 必須確認本次改動沒有破壞鏡像與核心頁面。
4. push 後再跑 `node tools/cross_validate_remote.cjs`。

## 3. Business Gate

這輪 Monetization MVP 的商業檢查只看 4 件事：

1. 收費閉環：首頁、題後、家長報告、明星題組都能走到升級流程。
2. 留存與轉換數據：trial、checkout、return、report、star pack 事件都有記錄。
3. 明星場景：分數、小數、百分率、生活應用題有明確入口與付費價值。
4. 家長週報：首屏能看懂摘要、弱點與下週動作。

## 4. 8-Hour Optimization Loop

每一輪 60 分鐘，連跑 8 輪，不要跨題亂改：

1. 選一個焦點：hint clarity / child wording / parent summary / chart fit。
2. 先跑 `tools/reviewer_solution_logic.cjs` 或既有 hint audit。
3. 只改一類問題。
4. 跑 validator。
5. 若 validator 全綠，再 commit。

建議輪替順序：

1. hint clarity
2. child wording
3. parent report summary
4. chart appropriateness
5. star pack wording
6. landing CTA clarity
7. remedial recommendation clarity
8. final regression + release note

直接入口：

1. 單次 reviewer 審查：`npm run reviewer:solution-logic:once`
2. 8 小時 reviewer 批次：`npm run reviewer:solution-logic:8h`
3. autonomous reviewer 別名：`npm run autonomous:8h:reviewer`

## 5. Recommended Commands

```powershell
c:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe tools/validate_all_elementary_banks.py
c:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/verify_all.py
node tools/reviewer_solution_logic.cjs --in_jsonl artifacts/questions_dump.jsonl --out artifacts/solution_logic_audit.json
node tools/run_reviewer_8h_batch.cjs --once
node tools/run_reviewer_8h_batch.cjs --hours 8 --interval-min 60
node tools/cross_validate_remote.cjs
```

## 6. Reviewer Agent Files

- `.github/sub-test-agent-instructions.md`
- `prompts/sub_test_agent_solution_reviewer.md`
- `tools/reviewer_solution_logic.cjs`

這三個檔案組合的目標不是取代主 validator，而是讓 8 小時持續優化時，先把「學生看不看得懂」與「家長能不能快速理解」變成可重複審查的流程。
