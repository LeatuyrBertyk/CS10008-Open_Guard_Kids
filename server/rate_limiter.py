"""Rate Limiting cho FastAPI (yêu cầu 2.2: giới hạn tần suất).

Sử dụng slowapi để chống:
- Brute-force đăng nhập
- Spam events/heartbeat
- DDoS nhỏ

Cấu hình:
- Login: tối đa 5 lần/phút/IP
- Heartbeat: tối đa 2 lần/phút/device (bình thường chỉ 1 lần/60s)
- Enroll: tối đa 3 lần/giờ/IP
- Events: tối đa 30 lần/phút/device
- API chung: 100 lần/phút/IP
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from shared.constants import RATE_LIMIT_DEFAULT


def get_remote_address_key(request: Request) -> str:
    """Lấy IP client (có xử lý X-Forwarded-For nếu chạy sau proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Lấy IP đầu tiên (client gốc)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Khởi tạo Limiter toàn cục
# key_func: lấy IP làm key (mỗi IP đếm riêng)
# default_limits: áp dụng cho mọi endpoint, có thể override
limiter = Limiter(
    key_func=get_remote_address_key,
    default_limits=[RATE_LIMIT_DEFAULT],   # "100/minute"
    storage_uri="memory://",               # dùng RAM, không cần Redis
    headers_enabled=True,                  # trả header X-RateLimit-*
)


# Giới hạn cụ thể cho từng loại endpoint
RATE_LIMIT_LOGIN = "5/minute"            # chống brute-force
RATE_LIMIT_HEARTBEAT = "2/minute"        # chỉ cần 1/phút, 2/min cho buffer
RATE_LIMIT_ENROLL = "3/hour"             # enroll hiếm khi cần
RATE_LIMIT_EVENTS = "30/minute"          # batch nhỏ, mỗi batch 1 lần
RATE_LIMIT_REQUESTS = "10/minute"        # con tạo request
RATE_LIMIT_AUTH_ME = "30/minute"         # xem thông tin


# ==========================================
# Exception handler
# ==========================================
async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Xử lý khi vượt rate limit - trả 429."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Quá nhiều yêu cầu. Vui lòng thử lại sau. (giới hạn: {exc.detail})",
            "retry_after": 60,
        },
        headers={"Retry-After": "60"},
    )


def setup_rate_limiting(app):
    """Đăng ký rate limiter cho FastAPI app.

    Args:
        app: FastAPI application
    """
    # Gắn limiter vào state để các router dùng @limiter.limit
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
