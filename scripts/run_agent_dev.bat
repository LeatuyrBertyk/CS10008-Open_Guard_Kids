@echo off
REM ==========================================
REM OGK Agent - Chạy ở chế độ dev (foreground)
REM ==========================================

echo ============================================================
echo  OGK Parental Control - Agent (DEV mode)
echo ============================================================
echo.

call conda activate computer_network 2>nul
if errorlevel 1 (
    echo [LỖI] Không tìm thấy conda environment 'computer_network'
    pause
    exit /b 1
)

cd /d "%~dp0.."

REM Kiểm tra đã enroll chưa
if not exist "agent\config.json" (
    echo [INFO] Chưa enroll. Chạy: python -m agent.enroll --code DEMO2024
    echo.
    set /p code="Nhập mã enroll (hoặc Enter để thoát): "
    if "%code%"=="" exit /b 1
    python -m agent.enroll --code %code%
)

REM Chạy agent
python -m agent.main --dev

pause
