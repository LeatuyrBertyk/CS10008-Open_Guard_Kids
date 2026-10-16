"""Router xử lý báo cáo tổng hợp cho dashboard."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.db.models import Child, User
from server.services import report_service
from server.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def get_summary(
    child_id: int = Query(..., description="ID của trẻ"),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy báo cáo tổng hợp cho 1 trẻ trong N ngày gần nhất."""
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Không tìm thấy trẻ")
    if child.parent_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền")

    summary = report_service.get_child_summary(db, child_id, days=days)
    if not summary:
        raise HTTPException(status_code=404, detail="Không có dữ liệu")
    return summary


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin tổng quan cho dashboard (tất cả con)."""
    return report_service.get_all_children_summary(db, current_user.id)
