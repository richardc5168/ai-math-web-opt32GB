@echo off
setlocal
cd /d %~dp0

REM Prefer venv python if available
if exist .venv\Scripts\python.exe (
  set PYEXE=.venv\Scripts\python.exe
) else (
  set PYEXE=py
)

REM Start server in this window
start "AIMATH API" cmd /k "%PYEXE% -m uvicorn server:app --host 127.0.0.1 --port 8001"

REM Open browser verification page
start "" "http://127.0.0.1:8001/verify"

echo If the browser opened too fast, refresh in a few seconds.
endlocal
