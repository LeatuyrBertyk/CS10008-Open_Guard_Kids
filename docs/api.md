# API Reference

## Authentication

Tất cả endpoint `/api/*` (trừ `/api/health`, `/api/auth/login`, `/api/devices/enroll`, `/api/events` Agent) yêu cầu JWT token.

Lấy token:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=admin123"
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

Sử dụng:
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

## Endpoints cho Agent (dùng device token)

| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/devices/enroll` | Đăng ký máy mới |
| POST | `/api/devices/heartbeat` | Heartbeat mỗi 60s |
| POST | `/api/events` | Đẩy sự kiện |
| POST | `/api/requests` | Con tạo yêu cầu |

### POST /api/devices/enroll

```bash
curl -X POST http://localhost:8000/api/devices/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "device_code": "DEMO2024",
    "hostname": "LAPTOP-AN",
    "os_version": "Windows 11 Pro",
    "mac_address": "AA:BB:CC:DD:EE:FF"
  }'
```

Response:
```json
{
  "device_id": 1,
  "device_token": "abc123...",
  "child_name": "Nguyễn Văn An",
  "policy": {
    "max_minutes_per_day": 120,
    "blocked_apps": [],
    "blocked_domains": [],
    "allowed_domains": [],
    "schedule": {},
    "bedtime_start": "22:00",
    "bedtime_end": "06:00"
  }
}
```

### POST /api/devices/heartbeat

```bash
curl -X POST http://localhost:8000/api/devices/heartbeat \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "usage_minutes_today": 45,
    "is_locked": false,
    "pending_events_count": 3
  }'
```

### POST /api/events

```bash
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "app_start",
        "app_name": "chrome",
        "duration_seconds": 0,
        "timestamp": "2024-01-15T10:30:00",
        "client_event_id": "uuid-1"
      }
    ]
  }'
```

## Endpoints cho Phụ huynh (cần JWT)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/auth/me` | Thông tin user |
| GET | `/api/devices` | Danh sách thiết bị |
| GET | `/api/devices/{id}/policy` | Xem policy |
| PUT | `/api/policies/{device_id}` | Cập nhật policy |
| GET | `/api/events?device_id=X` | Xem sự kiện |
| GET | `/api/requests?status=pending` | Xem yêu cầu |
| POST | `/api/requests/{id}/respond` | Phản hồi yêu cầu |
| GET | `/api/reports/summary?child_id=X` | Báo cáo tổng hợp |
| GET | `/api/reports/dashboard` | Tổng quan cho dashboard |

## Web Pages

| URL | Mô tả |
|---|---|
| `/` | Redirect → `/login` |
| `/login` | Trang đăng nhập |
| `/dashboard` | Tổng quan các máy |
| `/child/{id}` | Chi tiết 1 trẻ |
| `/child/{id}/policy` | Sửa policy |
| `/requests` | Xem yêu cầu từ con |
| `/docs` | FastAPI auto docs (Swagger) |
| `/api/health` | Health check |
