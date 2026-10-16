@echo off
REM ==========================================
REM Khởi tạo database
REM ==========================================

call conda activate computer_network 2>nul
if errorlevel 1 (
    echo [LỖI] Không tìm thấy conda environment 'computer_network'
    pause
    exit /b 1
)

cd /d "%~dp0.."

echo Đang khởi tạo database...
python -m server.db.init_db
echo.
pause
