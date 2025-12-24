Math Practice MVP — 快速上手

簡短說明：本專案提供一個本地 FastAPI 後端（`server.py`）與輕量題目引擎（`engine.py`），下列說明示範如何在本機執行測試流程或啟動伺服器。

## 先決條件
- Python 3.8+
- 建議使用虛擬環境 `.venv`
- 安裝相依：

```bash
pip install -r requirements.txt
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
python -m uvicorn server:app --reload --port 8000
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
```bash
python -m pytest test_ragweb_api.py -q
```

## 常見問題
- 如果 PowerShell 阻止執行 `.ps1`，暫時允許（僅當前 shell）：
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- 若 port 被占用，請改用其他 port（例：8002）或找出並結束占用的 PID。

如果要我把這些變更 commit，或再產生更詳細的使用手冊，請告訴我 `commit` 或 `more`。
