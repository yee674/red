@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ============================================================
echo   RedTrace AI  -  LAN public access (works offline)
echo ============================================================
echo.

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "..\data\.venv\Scripts\python.exe" set "PY=..\data\.venv\Scripts\python.exe"
if not defined PY (
    py -3 -c "import streamlit" >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    python -c "import streamlit" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [!] No Python with streamlit found.
    echo     Run "install-env.bat" first, or install streamlit manually.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
echo [1/2] Detecting local IP and generating the entry page ...
%PY% "%~dp0lan_info.py"

echo.
echo [2/2] Starting server on 0.0.0.0:8501 ...
echo       Keep this window open. Press Ctrl+C to stop.
echo.
%PY% -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false

pause
