@echo off
setlocal EnableExtensions

REM One-click Windows runner for interactive-g5-empire checks.
REM Usage:
REM   scripts\check_interactive_g5_empire.bat
REM   scripts\check_interactive_g5_empire.bat 3

set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

set "COUNT=%~1"
if "%COUNT%"=="" set "COUNT=20"

set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto :have_py

REM Fallback to py launcher if venv python is missing
set "PY=py"

:have_py
echo [1/3] Stability check (%COUNT% seeds)...
%PY% scripts\stability_check_interactive_g5_empire.py --count %COUNT%
if errorlevel 1 goto :fail

echo [2/3] Bank verify (strict kinds)...
%PY% scripts\verify_interactive_g5_empire_bank.py --strict-kinds
if errorlevel 1 goto :fail

echo [3/3] UI mapping verify (strict)...
%PY% scripts\verify_interactive_g5_empire_ui.py --strict
if errorlevel 1 goto :fail

echo OK: all checks passed.
popd >nul
exit /b 0

:fail
echo FAILED: check exited with errorlevel %errorlevel%.
popd >nul
exit /b 1
