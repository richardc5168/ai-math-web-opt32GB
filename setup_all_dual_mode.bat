@echo off
setlocal
title 🧠 Neo RAG 雙模式一鍵啟動 (Ollama / OpenAI)
color 0A

echo.
echo ======================================================
echo     Neo RAG 企業技術助理系統 (雙模式啟動)
echo ======================================================
echo.

cd /d "%~dp0"

REM === Step 1. 檢查 Python ===
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.10 以上版本。
    pause
    exit /b
)

REM === Step 2. 建立虛擬環境 ===
if not exist .venv (
    echo [建立虛擬環境中...]
    python -m venv .venv
)
call .venv\Scripts\activate

REM === Step 3. 安裝必要套件 ===
if not exist requirements.txt (
    echo [建立 requirements.txt] ...
    echo streamlit>=1.36.0>requirements.txt
    echo openai>=1.30.0>>requirements.txt
    echo requests>=2.31.0>>requirements.txt
    echo sentence-transformers>=2.6.1>>requirements.txt
    echo faiss-cpu>=1.8.0>>requirements.txt
    echo pypdf>=4.2.0>>requirements.txt
    echo python-docx>=1.1.0>>requirements.txt
)
echo [安裝依賴中...]
pip install --upgrade pip >nul
pip install -r requirements.txt

REM === Step 4. 偵測 OpenAI 是否可用 ===
set "MODE=offline"
if defined OPENAI_API_KEY (
    echo [檢查] 嘗試連線 OpenAI ...
    curl https://api.openai.com/v1/models -H "Authorization: Bearer %OPENAI_API_KEY%" -o nul -s
    if %errorlevel%==0 (
        set "MODE=online"
        echo [✅] OpenAI API 可用，使用雲端 GPT-4o-mini。
    ) else (
        echo [⚠️] 無法連線 OpenAI，自動改用離線模式。
    )
) else (
    echo [⚠️] 未設定 OPENAI_API_KEY，使用離線模式。
)

REM === Step 5. 若為離線模式，確保 Ollama 運作 ===
if "%MODE%"=="offline" (
    echo [離線模式] 啟動 Ollama ...
    curl http://localhost:11434/api/tags >nul 2>nul
    if %errorlevel% neq 0 (
        echo [提示] 嘗試啟動 Ollama ...
        start "" "C:\Program Files\Ollama\ollama.exe" serve
        timeout /t 5 >nul
    )
    echo [檢查模型 llama3.1:8b-instruct-q5_K_M] ...
    ollama list | find "llama3.1:8b-instruct-q5_K_M" >nul
    if %errorlevel% neq 0 (
        echo [下載模型中，約 5~10 分鐘] ...
        ollama pull llama3.1:8b-instruct-q5_K_M
    )
)

REM === Step 6. 建立 knowledge.db（若不存在） ===
if not exist knowledge.db (
    echo [建立 Neo 文件知識庫 (knowledge.db)] ...
    if exist ingest_neo_docs_sections.py (
        python ingest_neo_docs_sections.py
    ) else (
        echo [警告] 找不到 ingest_neo_docs_sections.py，跳過此步。
    )
)

REM === Step 7. 啟動 Streamlit 前端 ===
echo.
echo ======================================================
echo 啟動前端介面中...
echo 模式：%MODE%
echo ======================================================
if "%MODE%"=="offline" (
    setx OLLAMA_MODEL "llama3.1:8b-instruct-q5_K_M" >nul
    setx OLLAMA_HOST "http://localhost:11434" >nul
) else (
    setx OPENAI_MODEL "gpt-4o-mini" >nul
)
start "" http://localhost:8501
streamlit run app.py
pause
endlocal
