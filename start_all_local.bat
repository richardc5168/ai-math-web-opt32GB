@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set "API_PORT=8001"
set "ST_PORT=8501"

echo Starting FastAPI on http://127.0.0.1:%API_PORT% ...
if not exist "logs" mkdir logs
start "AIMATH API" /min cmd /c "%PY% -m uvicorn server:app --host 127.0.0.1 --port %API_PORT% > logs\uvicorn_%API_PORT%.log 2>&1"

echo Starting Streamlit on http://127.0.0.1:%ST_PORT% ...
start "AIMATH Streamlit" /min cmd /c "%PY% -m streamlit run app.py --server.port %ST_PORT% --server.address 127.0.0.1 > logs\streamlit_%ST_PORT%.log 2>&1"

REM Give servers a moment to start (avoid relying on timeout).
ping 127.0.0.1 -n 3 >nul

start "AIMATH Hub" http://127.0.0.1:%API_PORT%/verify
start "Quadratic" http://127.0.0.1:%API_PORT%/quadratic
start "Streamlit" http://127.0.0.1:%ST_PORT%

echo.
echo Opened:
echo - http://127.0.0.1:%API_PORT%/verify
echo - http://127.0.0.1:%API_PORT%/quadratic
echo - http://127.0.0.1:%ST_PORT%
echo.
echo If a port is in use, close the existing server or edit API_PORT/ST_PORT in this file.
echo Logs:
echo - logs\uvicorn_%API_PORT%.log
echo - logs\streamlit_%ST_PORT%.log
echo.
pause
