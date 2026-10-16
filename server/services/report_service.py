"""Service tổng hợp báo cáo cho dashboard."""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from server.db.models import Child, Device, Event, Policy


def get_child_summary(
    db: Session, child_id: int, days: int = 7
) -> Optional[dict]:
    """Tổng hợp báo cáo 7 ngày gần nhất cho 1 trẻ.

    Returns:
        Dict với các thông tin tổng hợp, hoặc None nếu child không tồn tại
    """
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        return None

    since = datetime.utcnow() - timedelta(days=days)

    # Tổng số phút dùng máy trong khoảng
    total_seconds = (
        db.query(func.coalesce(func.sum(Event.duration_seconds), 0))
        .join(Device, Device.id == Event.device_id)
        .filter(Device.child_id == child_id, Event.timestamp >= since)
        .scalar()
    )
    total_minutes = round(total_seconds / 60, 1) if total_seconds else 0

    # Tổng số lần bị chặn
    blocked_count = (
        db.query(func.count(Event.id))
        .join(Device, Device.id == Event.device_id)
        .filter(
            Device.child_id == child_id,
            Event.timestamp >= since,
            Event.event_type.in_(["app_blocked", "web_blocked"]),
        )
        .scalar()
    ) or 0

    # Lấy device đầu tiên (giả sử 1 trẻ = 1 máy cho đơn giản)
    device = db.query(Device).filter(Device.child_id == child_id).first()

    top_apps = []
    top_domains = []
    current_policy = None
    if device:
        from server.services.event_service import get_top_apps, get_top_domains
        top_apps = get_top_apps(db, device.id, days=days, limit=5)
        top_domains = get_top_domains(db, device.id, days=days, limit=5)
        if device.policy:
            from server.services.policy_service import policy_to_dict
            current_policy = policy_to_dict(device.policy)

    return {
        "child_id": child.id,
        "child_name": child.name,
        "period_days": days,
        "total_minutes": total_minutes,
        "blocked_count": blocked_count,
        "top_apps": top_apps,
        "top_domains": top_domains,
        "current_policy": current_policy,
        "device": {
            "id": device.id,
            "hostname": device.hostname,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "is_online": device.last_seen and (datetime.utcnow() - device.last_seen).seconds < 120,
        } if device else None,
    }


def get_all_children_summary(db: Session, parent_id: int) -> List[dict]:
    """Lấy summary ngắn gọn cho tất cả con của 1 phụ huynh."""
    children = db.query(Child).filter(Child.parent_id == parent_id).all()
    results = []
    for child in children:
        device = db.query(Device).filter(Device.child_id == child.id).first()
        results.append({
            "child_id": child.id,
            "child_name": child.name,
            "device_id": device.id if device else None,
            "device_hostname": device.hostname if device else "Chưa đăng ký",
            "is_online": (
                device.last_seen is not None
                and (datetime.utcnow() - device.last_seen).seconds < 120
            ) if device else False,
            "last_seen": device.last_seen.isoformat() if device and device.last_seen else None,
            "usage_today": device.last_usage_minutes if device else 0,
        })
    return results
