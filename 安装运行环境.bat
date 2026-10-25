@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Install dependencies into .venv (about 150 MB)
echo ============================================================
echo.

py -3 -m venv .venv || python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo [!] Could not create .venv. Please install Python 3.10+ first.
    pause
    exit /b 1
)

set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"

".venv\Scripts\python.exe" -m pip install --upgrade pip -i %PIP_INDEX% --trusted-host pypi.tuna.tsinghua.edu.cn
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i %PIP_INDEX% --trusted-host pypi.tuna.tsinghua.edu.cn

echo.
echo Done. Now double-click the launcher.
pause
