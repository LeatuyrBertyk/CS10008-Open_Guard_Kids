@echo off
REM ==========================================
REM OGK Server - Khởi động (Windows)
REM ==========================================

echo ============================================================
echo  OGK Parental Control - Server
echo ============================================================
echo.

REM Kích hoạt conda environment
call conda activate computer_network 2>nul
if errorlevel 1 (
    echo [LỖI] Không tìm thấy conda environment 'computer_network'
    echo        Chạy: conda env create -f environment.yml
    pause
    exit /b 1
)

REM Chuyển tới thư mục gốc project
cd /d "%~dp0.."

REM Khởi tạo database nếu chưa có
if not exist "server\ogk.db" (
    echo [INFO] Khởi tạo database lần đầu...
    python -m server.db.init_db
)

REM Chạy server
echo [INFO] Khởi động server tại http://127.0.0.1:8000
echo        Nhấn Ctrl+C để dừng
echo.
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

pause
