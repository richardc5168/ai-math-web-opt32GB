# AI Agent Workflow Instructions (Must Read)

## 🤖 For AI Assistants (Copilot, ChatGPT, Claude, etc.)
When modifying this repository, you **MUST** follow this rigorous validation protocol before and after any commit.

### 1. Pre-Commit Validation (Local Check)
Before committing ANY changes to bank files (JS/JSON) or logic:
1.  **Run Local Validation**: Ensure all local files are valid and consistently formatted.
    ```bash
    python tools/validate_all_elementary_banks.py
    ```
    *Criterion: Must output "ALL CHECKS PASSED".*

2.  **Run Full Build/Test** (if applicable):
    ```bash
    python tools/run_all.py --no-export
    ```

### 2. Post-Deployment Verification (Remote Cross-Check)
After verify push to `main` and GitHub Pages deployment (wait ~1-2 mins):
1.  **Run Remote Cross-Validation**: Confirm compatibility between local source and live site.
    ```bash
    node tools/cross_validate_remote.cjs
    ```
    *Criterion: Must output "SUMMARY: 17 PASSED, 0 FAILED".*
    *(Note: This tool compares local files against the live URL. It will only pass if local == remote.)*

---

Math Practice MVP — 快速上手

簡短說明：本專案提供一個本地 FastAPI 後端（`server.py`）與輕量題目引擎（`engine.py`），下列說明示範如何在本機執行測試流程或啟動伺服器。

## 先決條件
- Python 3.8+
- 建議使用虛擬環境 `.venv`
- 安裝相依：

PowerShell（Windows）:
```powershell
py -m pip install -r requirements.txt
```

macOS / Linux / WSL:
```bash
python -m pip install -r requirements.txt
```

## 一鍵在 Terminal 執行（不啟用 HTTP port）
此流程在 venv 的 Python 下直接執行內建 TestClient 流程（bootstrap → next → submit → custom → report）。

PowerShell（在專案根目錄）:
```powershell
.\scripts\run_terminal_flow.ps1
```

此腳本會使用 `.venv\Scripts\python.exe` 執行 `runner_temp.py`，並在流程結束後停在畫面等待按鍵。

## 啟動實際伺服器（開放 HTTP port）
在 venv activate 後啟動 uvicorn：

PowerShell:
```powershell
# 啟用 venv（若還沒啟動）
.\.venv\Scripts\Activate.ps1
# 啟動 server
py -m uvicorn server:app --reload --port 8000
```

cmd.exe:
```cmd
\.venv\Scripts\activate.bat
python -m uvicorn server:app --reload --port 8000
```

macOS / Linux / WSL:
```bash
source .venv/bin/activate
python -m uvicorn server:app --reload --port 8000
```

如果不想 activate，也可以直接呼叫 venv 的 python:
```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --port 8000
```

## 執行 smoke（真實 HTTP 流程）
啟動伺服器後，在另一個 terminal 執行：
```powershell
# 使用 runner_smoke.py（會啟動/停止 uvicorn 並執行整套請求）
.\.venv\Scripts\python.exe runner_smoke.py
```

或手動流程：
1. `POST /admin/bootstrap?name=...` 取得 `api_key`。
2. `POST /v1/questions/next?student_id=1` 取得 `question_id`。
3. `POST /v1/answers/submit` 提交答案。
4. `POST /v1/custom/solve` 自訂題目求解。
5. `GET /v1/reports/summary?student_id=1&days=30` 取得報表。

## 執行 pytest
在 venv 下執行針對本專案測試：
PowerShell（Windows）:
```powershell
py -m pytest test_ragweb_api.py -q
```

macOS / Linux / WSL:
```bash
python -m pytest test_ragweb_api.py -q
```

## 匯出「所有題型」題目/提示/答案（給外部模型做 QA）
用途：把 `engine.GENERATORS` 內所有題型都掃過，為每個題型生成多題（可固定 seed 可重現），並輸出成 JSONL + Markdown。

PowerShell（Windows）:
```powershell
./.venv/Scripts/python.exe scripts/export_all_questions.py --per_template 50 --seed 12345
```

輸出位置：
- `artifacts/questions_dump.jsonl`（一行一題，方便丟給 Gemini/GPT 做批次檢查）
- `artifacts/questions_dump.md`（人眼快速瀏覽）

參數：
- `--per_template N`：每個題型生成 N 題
- `--seed S`：固定 base seed（可重現）
- `--out_jsonl PATH` / `--out_md PATH`：指定輸出路徑

## 外部模型 QA（回饋檔驗證 + 摘要報告）
你可以把 `artifacts/questions_dump.jsonl` 丟給外部模型（Gemini / GPT-5 等）做 QA，
並要求它「只輸出 JSONL」。

QA 提示詞（繁體／台灣）：
- `prompts/external_llm_question_review_prompt_zh_tw.md`

外部模型輸出檔（建議存成）：
- `artifacts/question_reviews.jsonl`

驗證回饋檔格式：
```powershell
./.venv/Scripts/python.exe scripts/validate_question_reviews.py --in_jsonl artifacts/question_reviews.jsonl
```

產生摘要報告（方便你看哪些題型最需要改）：
```powershell
./.venv/Scripts/python.exe scripts/summarize_question_reviews.py --in_jsonl artifacts/question_reviews.jsonl --out_md artifacts/question_reviews_summary.md
```

## 半自動回填提示（產生 patch，人工確認後才套用）
目的：把外部模型的 `rewrite_hints` 整理成「每個題型一組候選提示」，產生 patch 檔讓你手動套用。

1) 先確認回饋檔格式正確：
```powershell
./.venv/Scripts/python.exe scripts/validate_question_reviews.py --in_jsonl artifacts/question_reviews.jsonl
```

2) 產生建議清單 + patch：
```powershell
./.venv/Scripts/python.exe scripts/apply_question_reviews.py --in_reviews artifacts/question_reviews.jsonl --in_dump artifacts/questions_dump.jsonl
```

輸出：
- `artifacts/review_apply/suggestions_by_template.md`
- `artifacts/review_apply/hint_overrides_candidates.patch`

3) 人工看過 patch 沒問題再套用：
```powershell
git apply artifacts/review_apply/hint_overrides_candidates.patch
```

4) 打開 `hint_overrides.py`，把你同意的題型 `approved` 改成 `True` 才會真的生效。

5) （建議）開啟 approved 前先跑回歸檢查：
```powershell
./.venv/Scripts/python.exe scripts/check_hint_overrides_regression.py --per_template 5 --seed 12345
```

## 常見問題
- 如果 PowerShell 阻止執行 `.ps1`，暫時允許（僅當前 shell）：
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- 若 port 被占用，請改用其他 port（例：8002）或找出並結束占用的 PID。

## 考前衝刺：錯題診斷 Gate
`docs/exam-sprint/index.html` 已加入錯題強制流程：

- 錯答後不可直接下一題（`Next` 會鎖住）
- 先看「錯誤診斷（Explain）」再看「補救提示（Ladder）」
- 必須按「我理解了」或按 `Enter` 才能繼續
- 錯題詳細記錄（錯誤類型、說明、補救提示、ack 行為）會存到既有本機紀錄，並出現在可複製報告內容

關鍵測試 selector：
- `data-testid="submit"`
- `data-testid="next"`
- `data-testid="wrong-diagnosis"`
- `data-testid="remedial-hints"`
- `data-testid="acknowledge"`

執行測試：
```powershell
npm install
node --test tests_js/diagnoseWrongAnswer.test.mjs
npx playwright install chromium
npm run test:e2e
```

如果要我把這些變更 commit，或再產生更詳細的使用手冊，請告訴我 `commit` 或 `more`。
