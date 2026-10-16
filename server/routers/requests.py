"""Router xử lý yêu cầu từ con: 'xin thêm giờ' / 'bị chặn nhầm'."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.db.models import Device, Child, Request as RequestModel, User
from server.services import policy_service
from server.services.audit_service import log_action
from server.auth import get_current_user, get_client_ip

# 2 router: agent tạo request, parent xem/respond
agent_router = APIRouter(prefix="/api/requests", tags=["requests-agent"])
parent_router = APIRouter(prefix="/api/requests", tags=["requests-parent"])


# ==========================================
# Agent tạo request (cần device token)
# ==========================================
@agent_router.post("")
def create_request(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    device: Device = Depends(__import__("server.routers.devices", fromlist=["require_device"]).require_device),
):
    """Con tạo yêu cầu: xin thêm giờ hoặc báo chặn nhầm.

    Payload:
    {
        "request_type": "extra_time" | "report_false_block",
        "reason": "Con cần hoàn thành bài tập",
        "extra_minutes": 30,
        "context": {"blocked_domain": "facebook.com"} (optional)
    }
    """
    request_type = payload.get("request_type", "")
    if request_type not in ("extra_time", "report_false_block"):
        raise HTTPException(status_code=400, detail="request_type không hợp lệ")

    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Vui lòng nhập lý do")

    extra_minutes = int(payload.get("extra_minutes", 15))
    if extra_minutes < 1 or extra_minutes > 120:
        extra_minutes = 15

    req = RequestModel(
        device_id=device.id,
        request_type=request_type,
        reason=reason,
        extra_minutes=extra_minutes,
        context=payload.get("context"),
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "status": "pending",
        "message": "Yêu cầu đã được gửi đến phụ huynh. Vui lòng chờ phản hồi.",
    }


# ==========================================
# Phụ huynh xem và phản hồi
# ==========================================
@parent_router.get("")
def list_requests(
    status: str = "pending",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phụ huynh xem danh sách yêu cầu (mặc định là pending)."""
    # Lấy tất cả children của parent
    children = db.query(Child).filter(Child.parent_id == current_user.id).all()
    child_ids = [c.id for c in children]
    devices = db.query(Device).filter(Device.child_id.in_(child_ids)).all() if child_ids else []
    device_ids = [d.id for d in devices]

    if not device_ids:
        return []

    query = db.query(RequestModel).filter(RequestModel.device_id.in_(device_ids))
    if status != "all":
        query = query.filter(RequestModel.status == status)

    requests = query.order_by(RequestModel.created_at.desc()).limit(200).all()

    result = []
    for r in requests:
        device = db.query(Device).filter(Device.id == r.device_id).first()
        child = db.query(Child).filter(Child.id == device.child_id).first() if device else None
        result.append({
            "id": r.id,
            "request_type": r.request_type,
            "reason": r.reason,
            "extra_minutes": r.extra_minutes,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "parent_response": r.parent_response,
            "grant_minutes": r.grant_minutes,
            "device_hostname": device.hostname if device else "?",
            "child_name": child.name if child else "?",
            "context": r.context,
        })
    return result


@parent_router.post("/{request_id}/respond")
def respond_request(
    request_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phụ huynh phản hồi yêu cầu.

    Payload:
    {
        "approved": true,
        "response_message": "Đồng ý, con cố gắng nhé",
        "grant_minutes": 30
    }
    """
    req = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")

    # Check quyền
    device = db.query(Device).filter(Device.id == req.device_id).first()
    child = db.query(Child).filter(Child.id == device.child_id).first() if device else None
    if not child or (child.parent_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Không có quyền")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Yêu cầu đã được phản hồi")

    approved = bool(payload.get("approved", False))
    response_msg = (payload.get("response_message") or "").strip()
    grant = int(payload.get("grant_minutes", 0))

    if not response_msg:
        raise HTTPException(status_code=400, detail="Vui lòng nhập phản hồi")

    req.status = "approved" if approved else "rejected"
    req.responded_at = datetime.utcnow()
    req.responded_by_user_id = current_user.id
    req.parent_response = response_msg
    req.grant_minutes = grant if approved else 0

    db.commit()

    # Nếu là xin thêm giờ và approved, cộng thêm giờ vào policy
    if approved and grant > 0 and req.request_type == "extra_time" and device:
        policy = policy_service.get_policy_by_device(db, device.id)
        if policy:
            policy.max_minutes_per_day += grant
            policy.updated_at = datetime.utcnow()
            db.commit()

    # Log
    log_action(
        db,
        username=current_user.username,
        action="respond_request",
        target=f"request:{req.id}",
        details={"approved": approved, "grant_minutes": grant, "type": req.request_type},
        ip_address=get_client_ip(request),
        user_id=current_user.id,
    )

    return {
        "id": req.id,
        "status": req.status,
        "message": "Phản hồi đã được gửi đến con",
    }
