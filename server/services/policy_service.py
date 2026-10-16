"""Service xử lý logic về Policy (luật áp dụng cho thiết bị)."""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from server.db.models import Policy, Device


def get_policy_by_device(db: Session, device_id: int) -> Optional[Policy]:
    """Lấy policy hiện tại của 1 device."""
    return db.query(Policy).filter(Policy.device_id == device_id).first()


def create_default_policy(db: Session, device_id: int) -> Policy:
    """Tạo policy mặc định khi enroll máy mới.

    Áp dụng: 2 tiếng/ngày, không chặn gì, lịch trống.
    """
    policy = Policy(
        device_id=device_id,
        max_minutes_per_day=120,
        blocked_apps=[],
        blocked_domains=[],
        allowed_domains=[],
        schedule={},
        bedtime_start="22:00",
        bedtime_end="06:00",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(
    db: Session,
    device_id: int,
    max_minutes_per_day: Optional[int] = None,
    blocked_apps: Optional[list] = None,
    blocked_domains: Optional[list] = None,
    allowed_domains: Optional[list] = None,
    schedule: Optional[dict] = None,
    bedtime_start: Optional[str] = None,
    bedtime_end: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[Policy]:
    """Cập nhật policy. Chỉ update những trường được truyền vào (không None)."""
    policy = get_policy_by_device(db, device_id)
    if not policy:
        return None

    if max_minutes_per_day is not None:
        policy.max_minutes_per_day = max_minutes_per_day
    if blocked_apps is not None:
        policy.blocked_apps = blocked_apps
    if blocked_domains is not None:
        policy.blocked_domains = blocked_domains
    if allowed_domains is not None:
        policy.allowed_domains = allowed_domains
    if schedule is not None:
        policy.schedule = schedule
    if bedtime_start is not None:
        policy.bedtime_start = bedtime_start
    if bedtime_end is not None:
        policy.bedtime_end = bedtime_end

    policy.updated_at = datetime.utcnow()
    if user_id is not None:
        policy.updated_by_user_id = user_id

    db.commit()
    db.refresh(policy)
    return policy


def policy_to_dict(policy: Policy) -> dict:
    """Chuyển Policy ORM object thành dict (để gửi cho Agent)."""
    return {
        "device_id": policy.device_id,
        "max_minutes_per_day": policy.max_minutes_per_day,
        "blocked_apps": policy.blocked_apps or [],
        "blocked_domains": policy.blocked_domains or [],
        "allowed_domains": policy.allowed_domains or [],
        "schedule": policy.schedule or {},
        "bedtime_start": policy.bedtime_start,
        "bedtime_end": policy.bedtime_end,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }
