@echo off
setlocal
cd /d "%~dp0"

set "PAGE=%CD%\docs\quadratic\index.html"
if not exist "%PAGE%" (
  echo Missing file: %PAGE%
  pause
  exit /b 1
)

echo Opening offline page (file://)...
start "Quadratic Offline" "%PAGE%"

echo.
echo Tip: If some browsers block file:// features, use start_quadratic_offline.bat.
echo.
pause
