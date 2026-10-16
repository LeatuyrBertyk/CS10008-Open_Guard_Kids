"""Router quản lý Policy (luật) - phụ huynh cập nhật luật cho từng thiết bị."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.db.models import Device, Child, User
from server.services import policy_service
from server.services.audit_service import log_action
from server.auth import get_current_user, get_client_ip

router = APIRouter(prefix="/api/policies", tags=["policies"])


def _check_permission(db: Session, device_id: int, current_user: User) -> Device:
    """Kiểm tra user có quyền với device này không, trả về device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    child = db.query(Child).filter(Child.id == device.child_id).first()
    if not child or (child.parent_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    return device


@router.put("/{device_id}")
def update_policy(
    device_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật policy cho 1 thiết bị.

    Payload có thể chứa bất kỳ trường nào (chỉ update trường có trong payload):
    - max_minutes_per_day
    - blocked_apps (list)
    - blocked_domains (list)
    - allowed_domains (list)
    - schedule (dict)
    - bedtime_start, bedtime_end
    """
    device = _check_permission(db, device_id, current_user)

    policy = policy_service.update_policy(
        db,
        device_id=device_id,
        max_minutes_per_day=payload.get("max_minutes_per_day"),
        blocked_apps=payload.get("blocked_apps"),
        blocked_domains=payload.get("blocked_domains"),
        allowed_domains=payload.get("allowed_domains"),
        schedule=payload.get("schedule"),
        bedtime_start=payload.get("bedtime_start"),
        bedtime_end=payload.get("bedtime_end"),
        user_id=current_user.id,
    )

    if not policy:
        raise HTTPException(status_code=404, detail="Chưa có policy")

    # Log
    log_action(
        db,
        username=current_user.username,
        action="update_policy",
        target=f"device:{device_id}",
        details=payload,
        ip_address=get_client_ip(request),
        user_id=current_user.id,
    )

    return policy_service.policy_to_dict(policy)
