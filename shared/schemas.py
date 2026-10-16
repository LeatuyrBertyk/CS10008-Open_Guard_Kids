"""Pydantic schemas (request/response) dùng chung.

Pydantic tự động validate kiểu dữ liệu khi nhận request,
đồng thời serialize khi trả response.
"""

from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# Cấu hình chung cho tất cả schema
# ==========================================
class _Base(BaseModel):
    """Base class cho mọi schema.

    - from_attributes=True: cho phép tạo schema từ SQLAlchemy ORM object
    - str_strip_whitespace=True: tự động strip whitespace
    """
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


# ==========================================
# Pagination (yêu cầu 2.2: phân trang)
# ==========================================
T = TypeVar("T")


class PaginationParams(_Base):
    """Query parameters cho phân trang.

    Sử dụng:
        @router.get("/items")
        def list_items(params: PaginationParams = Depends()):
            ...
    """
    page: int = Field(1, ge=1, description="Số trang, bắt đầu từ 1")
    page_size: int = Field(20, ge=1, le=100, description="Số item mỗi trang (1-100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PageInfo(_Base):
    """Thông tin về 1 trang."""
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PageResponse(_Base, Generic[T]):
    """Response có phân trang.

    Sử dụng:
        PageResponse[EventInfo](items=events, page_info=info)
    """
    items: List[T]
    page_info: PageInfo


# ==========================================
# Authentication
# ==========================================
class LoginRequest(_Base):
    """Schema cho POST /api/auth/login."""
    username: str = Field(..., min_length=1, max_length=64, examples=["admin"])
    password: str = Field(..., min_length=1, max_length=128, examples=["admin123"])


class TokenResponse(_Base):
    """Schema trả về sau khi đăng nhập thành công."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # số giây


class UserInfo(_Base):
    """Thông tin user trả về cho client."""
    id: int
    username: str
    role: str
    full_name: Optional[str] = None


# ==========================================
# Device & Enrollment
# ==========================================
class EnrollRequest(_Base):
    """Schema cho POST /api/devices/enroll.

    Agent gửi lên lần đầu tiên để đăng ký máy với server.
    """
    device_code: str = Field(..., min_length=4, max_length=64,
                             description="Mã đăng ký do phụ huynh tạo trên web")
    hostname: str = Field(..., min_length=1, max_length=128,
                          description="Tên máy tính của con")
    os_version: str = Field(..., max_length=128,
                            description="Phiên bản Windows, ví dụ: 'Windows 11 Pro 23H2'")
    mac_address: Optional[str] = Field(None, max_length=32)


class EnrollResponse(_Base):
    """Trả về sau khi enroll thành công.

    device_token phải được lưu an toàn trên máy con,
    dùng cho mọi request sau này.
    """
    device_id: int
    device_token: str
    child_name: str
    policy: dict  # PolicySchema - để tiện client có thể dùng


class HeartbeatRequest(_Base):
    """Schema cho POST /api/devices/heartbeat.

    Agent gửi định kỳ mỗi 60s để báo "tôi vẫn sống".
    """
    usage_minutes_today: int = Field(..., ge=0, description="Số phút đã dùng hôm nay")
    is_locked: bool = Field(False, description="Máy đang trong trạng thái khóa")
    pending_events_count: int = Field(0, ge=0, description="Số sự kiện chưa gửi lên server")


class HeartbeatResponse(_Base):
    """Server trả về sau heartbeat.

    Có thể kèm policy mới nếu phụ huynh vừa thay đổi.
    """
    ack: bool = True
    server_time: datetime
    policy_updated: bool = False
    new_policy: Optional[dict] = None  # PolicySchema nếu policy_updated=True
    force_lock: bool = False  # nếu True, Agent phải khóa máy ngay


class DeviceInfo(_Base):
    """Thông tin thiết bị trả về cho dashboard."""
    id: int
    hostname: str
    os_version: str
    last_seen: Optional[datetime]
    is_online: bool
    child_name: str
    usage_today_minutes: int = 0
    is_locked: bool = False


# ==========================================
# Policy (luật áp dụng cho 1 device)
# ==========================================
class PolicySchema(_Base):
    """Schema đầy đủ cho 1 bộ luật.

    blocked_apps: danh sách tên process (không có .exe), ví dụ ['chrome', 'steam']
    blocked_domains: danh sách domain cần chặn, ví dụ ['facebook.com', 'youtube.com']
    allowed_domains: danh sách miễn chặn vĩnh viễn (sẽ được tự động gộp với allowlist mặc định)
    schedule: lịch chặn, ví dụ:
        {
            "mon": [{"start": "19:00", "end": "21:00"}],  # T2 từ 19h-21h
            "tue": [],
            ...
        }
    """
    device_id: int
    max_minutes_per_day: int = Field(120, ge=0, le=1440)
    blocked_apps: List[str] = []
    blocked_domains: List[str] = []
    allowed_domains: List[str] = []
    schedule: dict = {}  # format: {"mon": [{"start": "HH:MM", "end": "HH:MM"}], ...}
    bedtime_start: Optional[str] = Field(None, description="HH:MM, ví dụ '22:00'")
    bedtime_end: Optional[str] = Field(None, description="HH:MM, ví dụ '06:00'")
    updated_at: Optional[datetime] = None


# ==========================================
# Events
# ==========================================
class EventSchema(_Base):
    """Schema cho 1 sự kiện gửi từ Agent lên Server.

    Siêu dữ liệu tối thiểu (theo nguyên tắc NT2):
    chỉ ghi tên app, tên miền, thời lượng, thời gian.
    KHÔNG ghi URL đầy đủ, nội dung, tiêu đề.
    """
    event_type: str = Field(..., max_length=32)
    app_name: Optional[str] = Field(None, max_length=128)
    domain: Optional[str] = Field(None, max_length=256)
    duration_seconds: int = Field(0, ge=0)
    timestamp: datetime
    client_event_id: Optional[str] = Field(None, max_length=64,
                                          description="ID phía Agent để chống trùng lặp")


class EventBatchRequest(_Base):
    """Gửi nhiều sự kiện cùng lúc để tiết kiệm băng thông."""
    events: List[EventSchema]


class EventBatchResponse(_Base):
    """Server trả về số sự kiện đã nhận."""
    accepted: int
    rejected: int = 0


# ==========================================
# Requests (xin thêm giờ, báo chặn nhầm)
# ==========================================
class RequestCreate(_Base):
    """Con tạo yêu cầu gửi lên server."""
    request_type: str = Field(..., pattern="^(extra_time|report_false_block)$")
    reason: str = Field(..., min_length=1, max_length=500,
                        help="Lý do, ví dụ: 'Con cần hoàn thành bài tập'")
    extra_minutes: int = Field(15, ge=1, le=120, description="Số phút xin thêm")
    context: Optional[dict] = Field(None, description="Thông tin kèm theo, ví dụ domain bị chặn nhầm")


class RequestInfo(_Base):
    """Thông tin 1 yêu cầu cho dashboard."""
    id: int
    request_type: str
    reason: str
    extra_minutes: int
    status: str
    created_at: datetime
    responded_at: Optional[datetime] = None
    parent_response: Optional[str] = None
    device_hostname: str
    child_name: str


class RequestRespond(_Base):
    """Phụ huynh phản hồi yêu cầu."""
    approved: bool
    response_message: str = Field(..., min_length=1, max_length=500)
    grant_minutes: int = Field(0, ge=0, le=120,
                               description="Nếu approved, cộng thêm bao nhiêu phút")


# ==========================================
# Reports
# ==========================================
class DailyUsageReport(_Base):
    """Báo cáo 1 ngày."""
    date: str  # YYYY-MM-DD
    total_minutes: int
    top_apps: List[dict]  # [{"name": "chrome", "minutes": 45}, ...]
    top_domains: List[dict]
    blocked_count: int


class SummaryReport(_Base):
    """Báo cáo tổng hợp 7 ngày gần nhất."""
    child_id: int
    child_name: str
    period_start: str
    period_end: str
    total_minutes: int
    daily_breakdown: List[DailyUsageReport]
    current_policy: Optional[PolicySchema] = None


# ==========================================
# Audit Log
# ==========================================
class AuditLogEntry(_Base):
    """1 dòng nhật ký kiểm toán."""
    id: int
    actor: str  # username
    action: str  # "login", "update_policy", "respond_request", ...
    target: Optional[str]  # mô tả đối tượng bị tác động
    details: Optional[dict]
    ip_address: Optional[str]
    timestamp: datetime
