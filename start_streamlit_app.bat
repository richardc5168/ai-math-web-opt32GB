@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting Streamlit app...
if not exist "logs" mkdir logs
start "AIMATH Streamlit" /min cmd /c "%PY% -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 > logs\streamlit_8501.log 2>&1"

ping 127.0.0.1 -n 3 >nul
start "AIMATH Streamlit" http://127.0.0.1:8501

echo.
echo Opened: http://127.0.0.1:8501
echo Log: logs\streamlit_8501.log
echo.
pause
