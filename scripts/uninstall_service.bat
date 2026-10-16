@echo off
REM ==========================================
REM Gỡ bỏ OGK Agent Windows Service
REM ==========================================

net session >nul 2>&1
if errorlevel 1 (
    echo [LỖI] Cần quyền Administrator
    pause
    exit /b 1
)

call conda activate computer_network 2>nul
cd /d "%~dp0.."

echo Đang dừng và gỡ service...
python -m agent.service stop
python -m agent.service remove

echo.
echo Đã gỡ xong.
pause
