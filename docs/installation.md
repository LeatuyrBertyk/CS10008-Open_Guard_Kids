# Hướng dẫn cài đặt chi tiết

> Mục đích: Cài đặt OGK Parental Control từ đầu trên máy Windows 10/11.

## 1. Chuẩn bị

### Yêu cầu phần cứng
- **Server (máy phụ huynh):** máy tính Windows/Mac/Linux, 4GB RAM, 1GB ổ cứng trống
- **Agent (máy của con):** Windows 10/11, 2GB RAM trống, 100MB ổ cứng
- **Mạng:** cùng LAN (hoặc mở port trên router cho truy cập từ xa)

### Yêu cầu phần mềm
- **Python 3.11+** (tải từ [python.org](https://www.python.org/downloads/))
- **Conda** (Miniconda hoặc Anaconda - [miniconda](https://docs.conda.io/en/latest/miniconda.html))
- **Git** (tùy chọn, để clone repo)

## 2. Cài đặt môi trường

### 2.1 Tạo Conda environment

```bash
conda env create -f environment.yml
conda activate computer_network
```

Lệnh này tạo env tên `computer_network` và cài tất cả thư viện cần thiết.

Nếu lỗi mạng, thử cài thủ công:

```bash
conda create -n computer_network python=3.11 -y
conda activate computer_network
pip install fastapi uvicorn[standard] sqlalchemy pydantic requests \
    python-jose[cryptography] bcrypt dnslib psutil pystray pillow \
    pytest httpx jinja2 python-multipart pywin32
```

### 2.2 Kiểm tra cài đặt

```bash
python -c "import fastapi, sqlalchemy, bcrypt, jose, dnslib, psutil, pystray, PIL; print('All OK')"
```

Nếu in ra `All OK` là thành công.

## 3. Khởi tạo Server

### 3.1 Khởi tạo database

```bash
python -m server.db.init_db
```

Hoặc trên Windows:
```bash
scripts\init_db.bat
```

Kết quả:
```
[1/3] Tạo bảng...      OK
[2/3] Tạo user admin... OK - user: admin / admin123
[3/3] Tạo dữ liệu mẫu... OK - child: Nguyễn Văn An (demo)
                                 OK - device: LAPTOP-DEMO
                                 OK - enroll code demo: DEMO2024
                                 OK - device token demo: demo-device-token-12345
```

### 3.2 (Tùy chọn) Tạo chứng chỉ HTTPS

Nếu muốn dùng HTTPS (khuyến nghị cho production):

```bash
# Cần OpenSSL (có sẵn trong Git Bash)
scripts\gen_cert.bat
```

Tạo ra `certs/cert.pem` và `certs/key.pem`. Set env:
```bash
set OGK_USE_HTTPS=true
set OGK_SSL_CERT=certs\cert.pem
set OGK_SSL_KEY=certs\key.pem
```

### 3.3 Khởi động Server

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Hoặc:
```bash
scripts\run_server.bat
```

Server chạy tại: **http://127.0.0.1:8000**

### 3.4 Truy cập lần đầu

1. Mở trình duyệt → http://127.0.0.1:8000
2. Đăng nhập:
   - Username: `admin`
   - Password: `admin123`
3. Đổi mật khẩu ngay (TODO: chức năng đổi mật khẩu trong Settings - sẽ có trong version sau)

## 4. Cài đặt Agent

### 4.1 Chuẩn bị mã enroll

1. Mở Dashboard http://127.0.0.1:8000/dashboard
2. Vào menu "Children" → tạo hồ sơ trẻ (tên, ngày sinh)
3. Mã enroll được tạo tự động, hoặc dùng `DEMO2024` cho demo

### 4.2 Cài đặt trên máy con

Có 2 cách:

#### Cách 1: Chạy thường (development)

```bash
# Bước 1: enroll
python -m agent.enroll --code DEMO2024

# Bước 2: chạy
python -m agent.main --dev
```

#### Cách 2: Cài Windows Service (khuyến nghị)

```bash
# Cần chạy với quyền Administrator!
scripts\install_service.bat
```

Service tên `OGKAgent` sẽ:
- Tự khởi động khi bật máy
- Chạy nền, không hiện cửa sổ
- Tự restart nếu crash

Để gỡ:
```bash
scripts\uninstall_service.bat
```

### 4.3 Kiểm tra Agent hoạt động

Trên máy con, kiểm tra:
- ✅ Biểu tượng 🛡️ xuất hiện ở khay hệ thống
- ✅ Click chuột phải → menu có "Mở bảng thông tin"
- ✅ Trong Dashboard server, máy hiện "🟢 Online"

Trong log của agent:
```
[INFO] Agent starting...
[INFO] EventQueue started
[INFO] Heartbeat started (interval=60s)
[INFO] ScreenTimeCounter started
[INFO] AppController started
[INFO] Agent started
```

## 5. Cấu hình nâng cao

### 5.1 Biến môi trường

Tạo file `.env` (cùng cấp `server/`) với nội dung:

```bash
# Server
OGK_SERVER_HOST=0.0.0.0
OGK_SERVER_PORT=8000

# Bảo mật - QUAN TRỌNG: đổi secret này!
OGK_JWT_SECRET=tao-mot-chuoi-bi-mat-dai-o-day-64-ky-tu
OGK_USE_HTTPS=true
OGK_SSL_CERT=certs\cert.pem
OGK_SSL_KEY=certs\key.pem

# Admin
OGK_ADMIN_USERNAME=admin
OGK_ADMIN_PASSWORD=mat-khau-man-hon

# Môi trường
OGK_ENV=production
```

Hoặc set trong Windows:
```cmd
setx OGK_JWT_SECRET "secret-dai-o-day-..."
```

### 5.2 Chạy nhiều máy Agent

Mỗi máy con:
1. Cài agent (như trên)
2. Enroll với mã riêng (tạo từ dashboard)
3. Cùng 1 server quản lý

Dashboard sẽ hiển thị tất cả các máy.

## 6. Khắc phục sự cố

### Lỗi: "ModuleNotFoundError: No module named 'X'"

→ Cài thêm thư viện: `pip install X`

### Lỗi: "Address already in use" khi khởi động server

→ Đổi port: `uvicorn server.main:app --port 8001`

### Lỗi: "Permission denied" khi start DNS proxy

→ Cần chạy với quyền Administrator, hoặc dùng port khác.

### Lỗi: Agent không hiện biểu tượng khay

→ Kiểm tra `pystray` đã cài: `pip install pystray pillow`
→ Trên Windows Server, khay hệ thống có thể bị tắt.

### Database bị lock

→ Tắt tất cả process dùng DB, hoặc xóa file `server/ogk.db-journal`.

### Không enroll được máy

→ Kiểm tra server có chạy không (`http://127.0.0.1:8000/api/health`)
→ Kiểm tra mã enroll còn hạn không
→ Kiểm tra firewall có chặn port 8000 không

## 7. Nâng cấp

Khi có phiên bản mới:

```bash
git pull  # nếu dùng git
conda activate computer_network
pip install -r requirements.txt --upgrade
python -m server.db.init_db  # KHÔNG chạy nếu muốn giữ data thật
```

Backup database trước khi nâng cấp:
```bash
copy server\ogk.db server\ogk.db.backup
```

## 8. Gỡ cài đặt

### Gỡ Agent
```bash
scripts\uninstall_service.bat
```

### Gỡ Server
- Tắt server (Ctrl+C)
- Xóa thư mục project
- (Tùy chọn) `conda env remove -n computer_network`
