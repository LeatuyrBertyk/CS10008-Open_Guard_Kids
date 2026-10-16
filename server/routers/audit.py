"""Router cho Audit Log (NT5: con xem được nhật ký thay đổi luật)."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.services.audit_service import get_logs_for_child, log_action
from server.services.ws_manager import ws_manager
from server.routers.devices import get_device_by_token, get_device_or_401
from shared.schemas import AuditLogEntry, PageInfo, PageResponse

router = APIRouter(prefix="/api", tags=["audit"])


# ==========================================
# Endpoint cho AGENT (dùng device token)
# Cho con xem nhật ký thay đổi policy của mình
# ==========================================
@router.get("/agent/audit-log", response_model=PageResponse[AuditLogEntry])
def get_my_audit_log(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    device=Depends(get_device_or_401),
):
    """Con (qua Agent) lấy nhật ký thay đổi luật của mình.

    Returns:
        Trang nhật ký (mới nhất trước) với thông tin:
        - ai thay đổi (parent username)
        - thay đổi gì (update_policy, respond_request, ...)
        - khi nào
        - chi tiết (giá trị cũ → mới)
    """
    from server.db.models import Child
    child = db.query(Child).filter(Child.id == device.child_id).first()
    if not child:
        return PageResponse(items=[], page_info=PageInfo(
            page=page, page_size=page_size, total=0, total_pages=0,
            has_next=False, has_prev=False,
        ))

    logs, total = get_logs_for_child(db, child.id, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    items = [AuditLogEntry.model_validate(log) for log in logs]

    return PageResponse(
        items=items,
        page_info=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


# ==========================================
# Endpoint cho PHỤ HUYNH (cần JWT)
# Xem nhật ký kiểm toán (mọi action)
# ==========================================
from server.auth import get_current_user  # noqa: E402
from server.db.models import User  # noqa: E402

@router.get("/audit", response_model=PageResponse[AuditLogEntry])
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phụ huynh xem nhật ký kiểm toán (mọi action)."""
    from server.services.audit_service import get_recent_logs

    offset = (page - 1) * page_size
    # Lấy tổng số
    total = db.query(__import__('server.db.models', fromlist=['AuditLog']).AuditLog).count()
    logs = (
        db.query(__import__('server.db.models', fromlist=['AuditLog']).AuditLog)
        .order_by(__import__('server.db.models', fromlist=['AuditLog']).AuditLog.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    items = [AuditLogEntry.model_validate(log) for log in logs]

    return PageResponse(
        items=items,
        page_info=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
