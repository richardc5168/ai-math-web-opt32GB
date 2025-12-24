@echo off
setlocal
title 🧠 Neo RAG + Ollama 一鍵離線啟動系統
color 0A

echo.
echo ==========================================================
echo   Neo RAG 離線版啟動程式 (含 Llama3.1:8b-instruct-q5_K_M)
echo ==========================================================
echo.

REM --- Step 1. 切換目錄 ---
cd /d "%~dp0"

REM --- Step 2. 檢查 Python 是否安裝 ---
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.10 以上版本。
    pause
    exit /b
)

REM --- Step 3. 檢查 Ollama 是否運作 ---
echo [檢查] Ollama 模型伺服器狀態...
curl http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
    echo [提示] Ollama 尚未啟動，嘗試啟動中...
    start "" "C:\Program Files\Ollama\ollama.exe" serve
    timeout /t 5 >nul
)

REM --- Step 4. 確認模型存在 ---
echo [檢查] 是否已下載模型 llama3.1:8b-instruct-q5_K_M ...
ollama list | find "llama3.1:8b-instruct-q5_K_M" >nul
if %errorlevel% neq 0 (
    echo [下載模型中，約 3~10 分鐘，僅需一次] ...
    ollama pull llama3.1:8b-instruct-q5_K_M
) else (
    echo [OK] 模型已存在。
)

REM --- Step 5. 建立虛擬環境（如尚未存在） ---
if not exist .venv (
    echo [建立虛擬環境中] ...
    python -m venv .venv
)
call .venv\Scripts\activate

REM --- Step 6. 安裝依賴套件 ---
if not exist requirements.txt (
    echo [建立 requirements.txt] ...
    echo streamlit>=1.36.0>requirements.txt
    echo requests>=2.31.0>>requirements.txt
    echo sentence-transformers>=2.6.1>>requirements.txt
    echo faiss-cpu>=1.8.0>>requirements.txt
    echo pypdf>=4.2.0>>requirements.txt
    echo python-docx>=1.1.0>>requirements.txt
)
echo [安裝依賴套件中...]
pip install --upgrade pip >nul
pip install -r requirements.txt

REM --- Step 7. 檢查資料庫是否存在 ---
if not exist knowledge.db (
    echo [建立 Neo 文件知識庫 (knowledge.db)] ...
    if exist ingest_neo_docs_sections.py (
        python ingest_neo_docs_sections.py
    ) else (
        echo [警告] 找不到 ingest_neo_docs_sections.py，跳過此步。
    )
)

REM --- Step 8. 啟動前端 ---
echo [啟動 Streamlit 前端] ...
start "" http://localhost:8501
streamlit run app.py

echo.
echo ----------------------------------------------------------
echo  ✅ 系統已啟動，可在瀏覽器開啟：
echo     http://localhost:8501
echo ----------------------------------------------------------
pause
endlocal
