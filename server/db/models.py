"""Định nghĩa các bảng (models) trong database.

Quan hệ chính:
    User (phụ huynh) 1 ── ∞ Child (trẻ)
    Child 1 ── ∞ Device (máy)
    Device 1 ── 1 Policy (luật)
    Device 1 ── ∞ Event (sự kiện)
    Device 1 ── ∞ Request (yêu cầu)
    User 1 ── ∞ AuditLog
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
    UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship

from server.db.session import Base


# ==========================================
# Bảng User - Tài khoản phụ huynh
# ==========================================
class User(Base):
    """Tài khoản phụ huynh / quản trị viên.

    Mỗi user có thể quản lý nhiều con (Child).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    # password_hash: lưu bcrypt hash, KHÔNG BAO GIỜ lưu plain text
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=True)
    role = Column(String(16), default="parent", nullable=False)  # 'parent' hoặc 'admin'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ
    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


# ==========================================
# Bảng Child - Hồ sơ trẻ
# ==========================================
class Child(Base):
    """Hồ sơ của 1 đứa trẻ được quản lý.

    1 child thuộc về 1 parent (User).
    1 child có thể có nhiều máy (Device) - laptop, desktop, ...
    """
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    birth_year = Column(Integer, nullable=True)
    avatar = Column(String(255), nullable=True)  # đường dẫn ảnh đại diện
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ
    parent = relationship("User", back_populates="children")
    devices = relationship("Device", back_populates="child", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Child id={self.id} name={self.name}>"


# ==========================================
# Bảng Device - Máy tính đã đăng ký
# ==========================================
class Device(Base):
    """Một máy tính (Windows) đã đăng ký với hệ thống.

    Mỗi device có 1 token duy nhất - Agent dùng token này để gọi API.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    hostname = Column(String(128), nullable=False)  # tên máy, ví dụ "LAPTOP-CON-AN"
    os_version = Column(String(128), nullable=True)
    mac_address = Column(String(32), nullable=True)

    # Token để Agent xác thực. Sinh ngẫu nhiên khi enroll.
    # Lưu hash, không lưu plain text.
    token_hash = Column(String(255), nullable=False, unique=True, index=True)

    # Trạng thái
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True)  # lần cuối Agent gửi heartbeat
    last_usage_minutes = Column(Integer, default=0, nullable=False)  # số phút dùng hôm nay
    is_locked = Column(Boolean, default=False, nullable=False)  # máy đang bị khóa

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ
    child = relationship("Child", back_populates="devices")
    policy = relationship("Policy", back_populates="device", uselist=False, cascade="all, delete-orphan")
    events = relationship("Event", back_populates="device", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device id={self.id} hostname={self.hostname}>"


# ==========================================
# Bảng Policy - Bộ luật áp dụng cho Device
# ==========================================
class Policy(Base):
    """Bộ luật chi tiết áp dụng cho 1 thiết bị.

    Mỗi Device có đúng 1 Policy (one-to-one).
    Policy chứa: giờ dùng tối đa, danh sách app chặn, danh sách web chặn, lịch.
    """
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"),
                       nullable=False, unique=True)

    # Giới hạn thời gian dùng máy mỗi ngày (phút)
    max_minutes_per_day = Column(Integer, default=120, nullable=False)

    # Danh sách process bị chặn (tên không có .exe)
    # Lưu dạng JSON array: ["chrome", "steam", "discord"]
    blocked_apps = Column(JSON, default=list, nullable=False)

    # Danh sách domain bị chặn
    # Lưu dạng JSON array: ["facebook.com", "youtube.com"]
    blocked_domains = Column(JSON, default=list, nullable=False)

    # Domain miễn chặn (kèm allowlist mặc định)
    allowed_domains = Column(JSON, default=list, nullable=False)

    # Lịch chặn theo ngày trong tuần
    # Format: {"mon": [{"start": "19:00", "end": "21:00"}], "tue": [], ...}
    schedule = Column(JSON, default=dict, nullable=False)

    # Giờ đi ngủ (khóa máy hoàn toàn, trừ khẩn cấp)
    bedtime_start = Column(String(5), nullable=True)  # "22:00"
    bedtime_end = Column(String(5), nullable=True)    # "06:00"

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Quan hệ
    device = relationship("Device", back_populates="policy")

    def __repr__(self):
        return f"<Policy device_id={self.device_id} max={self.max_minutes_per_day}min>"


# ==========================================
# Bảng Event - Nhật ký sự kiện
# ==========================================
class Event(Base):
    """Mỗi sự kiện (mở app, vào web, bị chặn...) ghi 1 dòng.

    Theo nguyên tắc NT2 - chỉ lưu siêu dữ liệu tối thiểu:
    tên app, tên miền, thời lượng, thời gian.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"),
                       nullable=False, index=True)

    event_type = Column(String(32), nullable=False)  # app_start, web_visit, app_blocked...
    app_name = Column(String(128), nullable=True)
    domain = Column(String(256), nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)

    timestamp = Column(DateTime, nullable=False, index=True)  # thời điểm xảy ra
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # thời điểm server nhận

    # ID duy nhất phía Agent để chống trùng khi retry
    client_event_id = Column(String(64), nullable=True, index=True)

    # Quan hệ
    device = relationship("Device", back_populates="events")

    # Index phức hợp để query nhanh theo device + thời gian
    __table_args__ = (
        Index("ix_events_device_time", "device_id", "timestamp"),
    )

    def __repr__(self):
        return f"<Event id={self.id} type={self.event_type} device={self.device_id}>"


# ==========================================
# Bảng Request - Yêu cầu từ con
# ==========================================
class Request(Base):
    """Yêu cầu 'xin thêm giờ' hoặc 'bị chặn nhầm' từ con.

    Theo nguyên tắc NT3: mọi yêu cầu phải được ghi nhận và phản hồi.
    """
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    request_type = Column(String(32), nullable=False)  # 'extra_time' hoặc 'report_false_block'
    reason = Column(Text, nullable=False)  # lý do con gửi
    extra_minutes = Column(Integer, default=15, nullable=False)  # số phút xin thêm

    context = Column(JSON, nullable=True)  # thông tin kèm theo (vd domain bị chặn)

    # Trạng thái: pending / approved / rejected
    status = Column(String(16), default="pending", nullable=False, index=True)

    # Phản hồi của phụ huynh
    responded_at = Column(DateTime, nullable=True)
    responded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_response = Column(Text, nullable=True)
    grant_minutes = Column(Integer, default=0, nullable=False)  # số phút thực sự cộng thêm

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Quan hệ
    device = relationship("Device", back_populates="requests")
    responded_by = relationship("User", foreign_keys=[responded_by_user_id])

    def __repr__(self):
        return f"<Request id={self.id} type={self.request_type} status={self.status}>"


# ==========================================
# Bảng AuditLog - Nhật ký kiểm toán
# ==========================================
class AuditLog(Base):
    """Ghi lại mọi hành động quan trọng của phụ huynh (và cả admin).

    Dùng để:
    - Trẻ xem "ai đổi luật, khi nào" (nguyên tắc NT5 - minh bạch 2 chiều)
    - Giáo viên / phụ huynh kiểm tra lịch sử thay đổi
    - Phát hiện truy cập bất thường
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null nếu là hệ thống
    username = Column(String(64), nullable=False)  # lưu cả khi user bị xóa
    action = Column(String(64), nullable=False)  # 'login', 'update_policy', ...
    target = Column(String(255), nullable=True)  # mô tả đối tượng (vd "device:5")
    details = Column(JSON, nullable=True)  # chi tiết bổ sung
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Quan hệ
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog id={self.id} action={self.action} user={self.username}>"
