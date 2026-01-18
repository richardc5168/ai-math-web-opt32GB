@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set "API_PORT=8001"
set "ST_PORT=8501"

if not exist "logs" mkdir logs

echo [1/2] Starting FastAPI (this window will stay open)...
start "AIMATH API DEBUG" cmd /k "%PY% -m uvicorn server:app --host 127.0.0.1 --port %API_PORT%"

echo [2/2] Starting Streamlit (this window will stay open)...
start "AIMATH Streamlit DEBUG" cmd /k "%PY% -m streamlit run app.py --server.port %ST_PORT% --server.address 127.0.0.1"

ping 127.0.0.1 -n 3 >nul
start "AIMATH Hub" http://127.0.0.1:%API_PORT%/verify
start "Quadratic" http://127.0.0.1:%API_PORT%/quadratic
start "Streamlit" http://127.0.0.1:%ST_PORT%

echo.
echo If you still see ERR_CONNECTION_REFUSED, check the two debug windows for errors.
echo.
pause
