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

## 常見問題
- 如果 PowerShell 阻止執行 `.ps1`，暫時允許（僅當前 shell）：
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- 若 port 被占用，請改用其他 port（例：8002）或找出並結束占用的 PID。

如果要我把這些變更 commit，或再產生更詳細的使用手冊，請告訴我 `commit` 或 `more`。
