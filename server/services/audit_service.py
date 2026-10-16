"""Service ghi nhật ký kiểm toán (Audit Log)."""

from typing import Optional
from sqlalchemy.orm import Session

from server.db.models import AuditLog, User


def log_action(
    db: Session,
    username: str,
    action: str,
    target: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_id: Optional[int] = None,
) -> AuditLog:
    """Ghi 1 dòng audit log.

    Args:
        db: session
        username: tên user thực hiện (lưu cả khi user bị xóa)
        action: hành động, ví dụ: 'login', 'update_policy', 'respond_request'
        target: mô tả đối tượng, ví dụ: 'device:5', 'request:12'
        details: chi tiết bổ sung dạng dict
        ip_address: IP của client
        user_id: ID user (có thể None nếu là hệ thống)
    """
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        target=target,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_recent_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    """Lấy các log gần đây nhất (cho admin/parent)."""
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_logs_for_child(
    db: Session,
    child_id: int,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    """Lấy audit log liên quan tới 1 trẻ (NT5: con xem được).

    Liên quan = action ảnh hưởng tới device của trẻ đó.
    Hiện tại target có dạng 'device:N' hoặc 'policy:N' - lọc theo device_id.

    Returns:
        (list_logs, total_count)
    """
    from server.db.models import Device, Policy

    # Lấy tất cả device_id của trẻ
    device_ids = [
        d.id for d in db.query(Device.id).filter(Device.child_id == child_id).all()
    ]
    if not device_ids:
        return [], 0

    # Lấy policy_id tương ứng
    policy_ids = [
        p.id for p in db.query(Policy.id).filter(Policy.device_id.in_(device_ids)).all()
    ]

    # Query logs có target chứa device_id hoặc policy_id
    query = db.query(AuditLog).filter(
        # target = 'device:N' với N thuộc device_ids
        # hoặc target = 'policy:N' với N thuộc policy_ids
        # Dùng like cho đơn giản
        AuditLog.action.in_([
            "update_policy", "create_policy", "delete_policy",
            "enroll_device", "remove_device", "lock_device", "unlock_device",
            "respond_request", "create_child", "delete_child",
        ])
    )

    # Lọc theo target (dạng 'type:id')
    # Vì SQLAlchemy không có regex trên SQLite, dùng like
    for did in device_ids:
        query = query.filter(
            (AuditLog.target == f"device:{did}") |
            (AuditLog.target.like(f"policy:{%"))  # sẽ filter kỹ bên dưới
        )

    # Cách đơn giản hơn: filter exact
    target_filters = [AuditLog.target == f"device:{did}" for did in device_ids]
    if target_filters:
        from sqlalchemy import or_
        query = db.query(AuditLog).filter(or_(*target_filters))
    else:
        return [], 0

    total = query.count()
    offset = (page - 1) * page_size
    logs = (
        query
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return logs, total
