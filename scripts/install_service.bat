@echo off
REM ==========================================
REM Cài đặt OGK Agent như Windows Service
REM ==========================================
REM Yêu cầu: chạy với quyền Administrator
REM ==========================================

echo ============================================================
echo  Cài đặt OGK Agent như Windows Service
echo ============================================================
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo [LỖI] Script này cần chạy với quyền Administrator
    echo        Click phải vào file ^> Run as administrator
    pause
    exit /b 1
)

call conda activate computer_network 2>nul
if errorlevel 1 (
    echo [LỖI] Không tìm thấy conda environment 'computer_network'
    pause
    exit /b 1
)

cd /d "%~dp0.."

echo [1/3] Dừng service nếu đang chạy...
python -m agent.service stop 2>nul

echo [2/3] Cài đặt service...
python -m agent.service install
if errorlevel 1 (
    echo [LỖI] Cài đặt thất bại
    pause
    exit /b 1
)

echo [3/3] Khởi động service...
python -m agent.service start
if errorlevel 1 (
    echo [CẢNH BÁO] Service chưa start được. Thử: sc start OGKAgent
)

echo.
echo ============================================================
echo  HOÀN TẤT
echo ============================================================
echo  Service đã được cài. Xem trong Services (services.msc)
echo  Tên service: OGKAgent
echo.
echo  Để gỡ bỏ: chạy scripts\uninstall_service.bat
echo ============================================================
pause
