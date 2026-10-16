"""Router xử lý thiết bị: enroll, heartbeat, danh sách."""

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

import bcrypt

from server.db.session import get_db
from server.db.models import Device, Child, Policy, User
from server.services import policy_service
from server.services.audit_service import log_action
from server.auth import get_current_user, get_client_ip

router = APIRouter(prefix="/api/devices", tags=["devices"])


# ==========================================
# Helper: xác thực thiết bị bằng token
# ==========================================
def get_device_by_token(db: Session, token: str) -> Optional[Device]:
    """Tìm device bằng token. Token được so sánh qua bcrypt."""
    if not token:
        return None
    # Lấy tất cả device active rồi check token (vì token được hash)
    # Trong production nên dùng index/lookup hiệu quả hơn
    devices = db.query(Device).filter(Device.is_active == True).all()  # noqa
    for dev in devices:
        try:
            if bcrypt.checkpw(token.encode("utf-8"), dev.token_hash.encode("utf-8")):
                return dev
        except Exception:
            continue
    return None


def require_device(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Device:
    """Dependency: bắt buộc có Bearer token là device token hợp lệ."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Authorization header",
        )
    token = authorization[7:]  # bỏ "Bearer "
    device = get_device_by_token(db, token)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token không hợp lệ",
        )
    return device


# ==========================================
# Endpoints cho Phụ huynh (cần JWT)
# ==========================================
@router.get("/")
def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phụ huynh xem danh sách tất cả thiết bị của mình quản lý."""
    children = db.query(Child).filter(Child.parent_id == current_user.id).all()
    child_ids = [c.id for c in children]

    devices = db.query(Device).filter(Device.child_id.in_(child_ids)).all() if child_ids else []
    result = []
    for d in devices:
        child = db.query(Child).filter(Child.id == d.child_id).first()
        result.append({
            "id": d.id,
            "hostname": d.hostname,
            "os_version": d.os_version,
            "child_id": d.child_id,
            "child_name": child.name if child else "?",
            "is_online": d.last_seen and (datetime.utcnow() - d.last_seen).seconds < 120,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "usage_today": d.last_usage_minutes,
            "is_locked": d.is_locked,
        })
    return result


# ==========================================
# Endpoints cho Agent (dùng device token)
# ==========================================
@router.post("/enroll")
def enroll_device(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Agent đăng ký máy mới. Cần mã enroll_code hợp lệ.

    Trong demo, enroll_code là 'DEMO2024' hoặc lấy từ bảng Child.
    Trong production, nên tạo bảng EnrollCode riêng với thời hạn.
    """
    from server.config import DEFAULT_ADMIN_USERNAME  # noqa

    device_code = payload.get("device_code", "")
    hostname = payload.get("hostname", "")
    os_version = payload.get("os_version", "")
    mac_address = payload.get("mac_address")

    if not device_code or not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu device_code hoặc hostname",
        )

    # Tìm child theo mã enroll
    # Đơn giản: tìm child có tên chứa mã này, hoặc dùng mã DEMO2024
    child = None
    if device_code.upper() == "DEMO2024":
        child = db.query(Child).first()  # lấy child đầu tiên
    else:
        # Thử tìm theo id (nếu mã là số)
        try:
            child_id = int(device_code)
            child = db.query(Child).filter(Child.id == child_id).first()
        except ValueError:
            pass

    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã đăng ký không hợp lệ hoặc không tìm thấy trẻ tương ứng",
        )

    # Sinh token ngẫu nhiên
    new_token = secrets.token_urlsafe(32)
    token_hash = bcrypt.hashpw(new_token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Tạo device
    device = Device(
        child_id=child.id,
        hostname=hostname,
        os_version=os_version,
        mac_address=mac_address,
        token_hash=token_hash,
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    # Tạo policy mặc định
    policy = policy_service.create_default_policy(db, device.id)

    # Log
    log_action(
        db,
        username="system",
        action="device_enroll",
        target=f"device:{device.id}",
        details={"hostname": hostname, "child_id": child.id},
        ip_address=get_client_ip(request),
    )

    return {
        "device_id": device.id,
        "device_token": new_token,  # chỉ trả 1 lần này
        "child_name": child.name,
        "policy": policy_service.policy_to_dict(policy),
    }


@router.post("/heartbeat")
def heartbeat(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device),
):
    """Agent gửi heartbeat mỗi 60s.

    Payload:
    {
        "usage_minutes_today": 45,
        "is_locked": false,
        "pending_events_count": 3
    }
    """
    usage_minutes = int(payload.get("usage_minutes_today", 0))
    is_locked = bool(payload.get("is_locked", False))

    device.last_seen = datetime.utcnow()
    device.last_usage_minutes = usage_minutes
    device.is_locked = is_locked
    db.commit()

    # Lấy policy hiện tại
    policy = policy_service.get_policy_by_device(db, device.id)
    policy_dict = policy_service.policy_to_dict(policy) if policy else None

    # Kiểm tra xem có cần force lock không (vd quá giờ)
    force_lock = False
    if policy and usage_minutes >= policy.max_minutes_per_day and not is_locked:
        force_lock = True
        device.is_locked = True
        db.commit()

    return {
        "ack": True,
        "server_time": datetime.utcnow().isoformat(),
        "policy_updated": False,  # TODO: so sánh với policy Agent đang giữ
        "new_policy": policy_dict,
        "force_lock": force_lock,
    }


@router.get("/{device_id}/policy")
def get_device_policy(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phụ huynh xem policy của 1 device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    # Check quyền
    child = db.query(Child).filter(Child.id == device.child_id).first()
    if not child or child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")

    policy = policy_service.get_policy_by_device(db, device_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Chưa có policy")
    return policy_service.policy_to_dict(policy)
