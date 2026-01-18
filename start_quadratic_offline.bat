@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting AIMATH API (quadratic)...
if not exist "logs" mkdir logs
start "AIMATH API" /min cmd /c "%PY% -m uvicorn server:app --host 127.0.0.1 --port 8001 > logs\uvicorn_8001.log 2>&1"

ping 127.0.0.1 -n 2 >nul
start "Quadratic" http://127.0.0.1:8001/quadratic

echo.
echo Opened: http://127.0.0.1:8001/quadratic
echo Log: logs\uvicorn_8001.log
echo If port 8001 is in use, close the other server or change port in this .bat.
echo.
pause
