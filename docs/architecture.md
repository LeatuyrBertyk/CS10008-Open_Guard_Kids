# Kiến trúc hệ thống

## Tổng quan

OGK Parental Control gồm 2 phần chính:

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   OGK-Agent             │  HTTPS  │   OGK-Server            │
│   (máy của trẻ)         │ <-----> │   (FastAPI + SQLite)    │
│                         │  60s    │                         │
│  + Service (SYSTEM)     │ heartbeat│ + Dashboard web        │
│  + Tray UI (user)       │         │ + REST API              │
└─────────────────────────┘         └─────────────────────────┘
```

## Các module trong OGK-Agent

| Module | Chức năng | Thread |
|---|---|---|
| `agent.client` | HTTP client gọi server | - |
| `agent.local_cache` | SQLite local (khi mất mạng) | - |
| `agent.events` | Hàng đợi sự kiện + flush định kỳ | ✅ |
| `agent.heartbeat` | Gửi tín hiệu mỗi 60s | ✅ |
| `agent.screentime` | Đếm thời gian dùng máy | ✅ |
| `agent.app_controller` | Chặn ứng dụng bằng psutil | ✅ |
| `agent.dns_proxy` | DNS mini server lọc domain | ✅ |
| `agent.local_server` | HTTP IPC cho Tray UI | ✅ |
| `agent.tray_ui` | Biểu tượng khay + cửa sổ | ✅ |

## Các module trong OGK-Server

| Module | Chức năng |
|---|---|
| `server.main` | FastAPI app, route chính |
| `server.auth` | JWT + bcrypt |
| `server.db.models` | SQLAlchemy ORM |
| `server.routers.*` | API endpoints theo nhóm |
| `server.services.*` | Business logic |
| `server.templates/*` | HTML cho dashboard |

## Cơ sở dữ liệu

Xem chi tiết trong `server/db/models.py`. Có 7 bảng:

- `users` - tài khoản phụ huynh
- `children` - hồ sơ trẻ
- `devices` - máy đã đăng ký
- `policies` - luật cho mỗi máy
- `events` - nhật ký hoạt động
- `requests` - yêu cầu xin thêm giờ / bị chặn nhầm
- `audit_log` - nhật ký kiểm toán

## Bảo mật

| Lớp | Cách xử lý |
|---|---|
| Mật khẩu | Bcrypt (12 rounds) |
| API cho user | JWT (HS256, 24h) |
| API cho device | Token sinh ngẫu nhiên, hash lưu DB |
| Truyền thông | HTTPS (self-signed cho demo) |
| CORS | Cho phép `*` (giới hạn trong production) |

## Đảm bảo nguyên tắc "Minh bạch với trẻ"

| NT | Cách hiện thực |
|---|---|
| NT1: Con biết | Biểu tượng khay + thông báo |
| NT2: Tối thiểu | Chỉ lưu metadata, không lưu nội dung |
| NT3: Con có tiếng nói | API `/api/requests` |
| NT4: Giải thích được | Tray UI hiện lý do chặn |
| NT5: Minh bạch 2 chiều | Dashboard + audit_log |
| NT6: An toàn | `shared/allowlist.py` |
