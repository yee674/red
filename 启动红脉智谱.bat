@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   RedTrace AI - local launcher (this PC only)
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
    echo     Run "install-env.bat" once, or:
    echo         python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Using: %PY%
echo.
%PY% -m streamlit run app.py

pause
