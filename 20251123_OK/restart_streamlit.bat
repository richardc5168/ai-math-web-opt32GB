@echo off
setlocal
title 🚀 Neo RAG 啟動器 (GPT-4o / Llama 雙模式)

REM === 基本設定 ===
set PORT=8507
set ADDRESS=0.0.0.0
set APP_FILE=app.py

echo.
echo =============================================
echo 🧠 Neo RAG 啟動器
echo Port: %PORT%
echo Address: %ADDRESS%
echo =============================================
echo.

REM === 刪除舊的埠 ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT%') do (
    echo ⚠️  釋放佔用的 port %PORT% (PID=%%a)...
    taskkill /PID %%a /F >nul 2>&1
)
echo ✅ Port %PORT% 可用
echo.

REM === 啟動虛擬環境 ===
if not exist .venv (
    echo ❌ 找不到虛擬環境 .venv
    echo 請先執行：python -m venv .venv
    pause
    exit /b
)
call .venv\Scripts\activate

REM === 偵測 GPT-4o 連線狀態 ===
echo 🔍 檢查 OpenAI API Key 狀態...
python - <<PYCODE
import os
from openai import OpenAI
key = os.getenv("OPENAI_API_KEY")
if not key:
    print("❌ 未設定 OPENAI_API_KEY，僅能離線使用")
else:
    try:
        client = OpenAI(api_key=key)
        models = [m.id for m in client.models.list().data if "gpt-4o" in m.id]
        if models:
            print(f"✅ 偵測到 GPT-4o 模型可用：{models[0]}")
        else:
            print("⚠️ 未偵測到 GPT-4o，將使用離線模式")
    except Exception as e:
        print(f"⚠️ 無法連線至 OpenAI：{e}\n→ 自動切換離線模式")
PYCODE

echo.
echo 🚀 啟動 Streamlit 伺服器中...
start "" streamlit run %APP_FILE% --server.address %ADDRESS% --server.port %PORT%

REM === 自動開啟瀏覽器 ===
timeout /t 5 >nul
echo 🌐 自動開啟瀏覽器 http://localhost:%PORT%
start msedge http://localhost:%PORT%

echo.
echo ✅ 伺服器已啟動，請查看瀏覽器。
pause
endlocal
