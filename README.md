# OGK Parental Control

**Công cụ đồng hành, không phải phần mềm theo dõi lén**

Đồ án cuối kỳ môn Mạng máy tính - CS10008.

## Tính năng

- **Giám sát siêu dữ liệu tối thiểu** (chỉ tên app, tên miền, thời lượng - KHÔNG nội dung)
- **Chặn ứng dụng & website** theo lịch do phụ huynh đặt
- **Giới hạn thời gian dùng máy** mỗi ngày
- **Dashboard web** cho phụ huynh xem báo cáo
- **Nút "Xin thêm giờ"** cho con - có phản hồi từ bố mẹ
- **Biểu tượng khay hệ thống** luôn hiển thị (minh bạch)
- **Allowlist khẩn cấp** - luôn cho phép gọi 111, vào web trường
- **Audit log** - mọi thay đổi luật đều được ghi lại

## Yêu cầu hệ thống

- Windows 10/11 (x64)
- Python 3.11+
- Conda (Miniconda hoặc Anaconda)

## Cài đặt

### 1. Tạo môi trường ảo

```bash
conda env create -f environment.yml
conda activate computer_network
```

### 2. Cài thêm thư viện phụ

```bash
pip install pystray pillow dnslib bcrypt python-jose[cryptography] passlib pytest httpx pytest-cov
```

### 3. Khởi tạo database

```bash
python -m server.db.init_db
```

Hoặc trên Windows:
```bash
scripts\init_db.bat
```

## Chạy nhanh (demo)

### Bước 1: Khởi động Server

Terminal 1:
```bash
conda activate computer_network
python -m uvicorn server.main:app --reload
```

Hoặc:
```bash
scripts\run_server.bat
```

Server chạy tại: http://127.0.0.1:8000

### Bước 2: Đăng nhập Dashboard

Mở trình duyệt: http://127.0.0.1:8000

Đăng nhập với:
- Username: `admin`
- Password: `admin123`

### Bước 3: Đăng ký máy Agent

Terminal 2:
```bash
conda activate computer_network
python -m agent.enroll --code DEMO2024
```

### Bước 4: Chạy Agent

```bash
python -m agent.main --dev
```

Hoặc:
```bash
scripts\run_agent_dev.bat
```

## Cài đặt dạng Windows Service (production)

```bash
# Cần chạy với quyền Administrator
scripts\install_service.bat
```

Sau khi cài, service tên `OGKAgent` sẽ tự chạy khi bật máy.

Để gỡ: `scripts\uninstall_service.bat`

## Chạy test

```bash
pytest                    # Tất cả test
pytest -v                 # Verbose
pytest --cov=server --cov=agent  # Đo coverage
pytest -m unit            # Chỉ test unit
```

## Cấu trúc thư mục

```
CS10008-Parental_Control_Software/
├── shared/              # Code dùng chung
│   ├── constants.py
│   ├── schemas.py
│   └── allowlist.py
├── server/              # FastAPI server
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── db/
│   ├── routers/
│   ├── services/
│   ├── templates/       # HTML dashboard
│   ├── static/          # CSS, JS
│   └── tests/
├── agent/               # Phần mềm trên máy con
│   ├── main.py
│   ├── service.py       # Windows Service
│   ├── config.py
│   ├── client.py
│   ├── enroll.py
│   ├── heartbeat.py
│   ├── events.py
│   ├── local_cache.py
│   ├── screentime.py
│   ├── app_controller.py
│   ├── dns_proxy.py
│   ├── tray_ui.py
│   ├── local_server.py
│   └── tests/
├── scripts/             # Script .bat
├── docs/                # Tài liệu
│   ├── architecture.md
│   ├── api.md
│   └── security.md
├── environment.yml
└── README.md (file này)
```

## Cấu hình nâng cao

Qua biến môi trường:

| Biến | Mặc định | Mô tả |
|---|---|---|
| `OGK_SERVER_HOST` | 127.0.0.1 | Host server |
| `OGK_SERVER_PORT` | 8000 | Port server |
| `OGK_JWT_SECRET` | (mặc định dev) | Secret JWT |
| `OGK_USE_HTTPS` | false | Bật HTTPS |
| `OGK_ADMIN_USERNAME` | admin | User admin |
| `OGK_ADMIN_PASSWORD` | admin123 | Password admin |

Ví dụ:
```bash
# Windows CMD
set OGK_JWT_SECRET=my_super_secret_key
python -m uvicorn server.main:app

# PowerShell
$env:OGK_JWT_SECRET="my_super_secret_key"
python -m uvicorn server.main:app
```

## Nguyên tắc thiết kế (BẮT BUỘC)

1. **Con phải biết phần mềm đang chạy** - luôn có biểu tượng khay
2. **Chỉ thu thập siêu dữ liệu tối thiểu** - không lưu nội dung
3. **Con có tiếng nói** - có nút xin thêm giờ, báo chặn nhầm
4. **Mọi hành động phải giải thích được** - khi chặn, kèm lý do
5. **Minh bạch hai chiều** - con xem được báo cáo + log phụ huynh
6. **An toàn tuyệt đối** - luôn cho phép gọi khẩn cấp

## Cảnh báo

⚠️ **Phần mềm này chỉ dành cho mục đích giáo dục và đồ án.**

- KHÔNG cài lên máy người khác khi chưa được phép
- KHÔNG dùng để theo dõi người lớn (vi phạm pháp luật)
- KHÔNG dùng để kiểm soát, gây áp lực lên trẻ
- NÊN thông báo rõ ràng với trẻ về sự tồn tại của phần mềm

## Tác giả

Đồ án CS10008 - Mạng máy tính

## License

Chỉ dùng cho mục đích học tập.
