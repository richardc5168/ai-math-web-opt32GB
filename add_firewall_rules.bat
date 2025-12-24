@echo off
echo ======================================================
echo  🔐 自動設定防火牆：允許 Python / Streamlit 通過
echo ======================================================

REM 要求系統管理員權限
NET SESSION >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo 請以系統管理員模式執行此批次檔！
    pause
    exit /b
)

REM 加入 Python.exe
set PYTHON_PATH=C:\Users\Richard\AppData\Local\Programs\Python\Python313\python.exe
if exist "%PYTHON_PATH%" (
    echo ✅ 加入防火牆允許：%PYTHON_PATH%
    netsh advfirewall firewall add rule name="Allow Python" dir=in action=allow program="%PYTHON_PATH%" enable=yes profile=private
) else (
    echo ⚠️ 找不到 Python.exe：%PYTHON_PATH%
)

REM 加入 Streamlit.exe
set STREAMLIT_PATH=C:\Users\Richard\Documents\RAG\.venv\Scripts\streamlit.exe
if exist "%STREAMLIT_PATH%" (
    echo ✅ 加入防火牆允許：%STREAMLIT_PATH%
    netsh advfirewall firewall add rule name="Allow Streamlit" dir=in action=allow program="%STREAMLIT_PATH%" enable=yes profile=private
) else (
    echo ⚠️ 找不到 Streamlit.exe：%STREAMLIT_PATH%
)

echo ------------------------------------------------------
echo 🎯 設定完成！現在可以執行：
echo     streamlit run app.py --server.port 8505
echo ------------------------------------------------------
pause
