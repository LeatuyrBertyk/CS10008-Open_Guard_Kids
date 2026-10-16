@echo off
REM ==========================================
REM Tạo chứng chỉ TLS tự ký (cho HTTPS demo)
REM ==========================================

call conda activate computer_network 2>nul

cd /d "%~dp0.."

if not exist "certs" mkdir certs

echo Đang tạo chứng chỉ self-signed tại certs\...
openssl req -x509 -newkey rsa:4096 -nodes ^
    -keyout certs\key.pem ^
    -out certs\cert.pem ^
    -days 365 ^
    -subj "/C=VN/ST=HCM/L=HCM/O=OGK/OU=Dev/CN=localhost"

if errorlevel 1 (
    echo [LỖI] openssl chưa được cài. Tải từ: https://slproweb.com/products/Win32OpenSSL.html
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Đã tạo cert tại certs\cert.pem và certs\key.pem
echo  Để dùng HTTPS: set OGK_USE_HTTPS=true và chạy server
echo ============================================================
pause
