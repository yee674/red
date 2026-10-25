@echo off
chcp 65001 >nul
echo ============================================================
echo   Allow incoming TCP 8501 (requires administrator)
echo ============================================================
echo.

net session >nul 2>nul
if errorlevel 1 (
    echo [!] Please right-click this file and choose "Run as administrator".
    pause
    exit /b 1
)

netsh advfirewall firewall delete rule name="RedTraceAI-8501" >nul 2>nul
netsh advfirewall firewall add rule name="RedTraceAI-8501" dir=in action=allow protocol=TCP localport=8501 profile=private,domain

echo.
if errorlevel 1 (
    echo [!] Failed. Allow it manually: Control Panel - Windows Defender Firewall - Allow an app
) else (
    echo [OK] Port 8501 allowed for private/domain networks.
)
echo.
pause
