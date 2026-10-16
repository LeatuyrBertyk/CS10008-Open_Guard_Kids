"""Router xử lý sự kiện: Agent gửi lên, phụ huynh xem.

Tích hợp:
- Rate limiting (slowapi)
- Phân trang (page, page_size)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from server.db.session import get_db
from server.db.models import Event, Device, Child, User
from server.services import event_service
from server.auth import get_current_user
from server.rate_limiter import limiter
from shared.constants import (
    RATE_LIMIT_EVENTS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE,
)
from shared.schemas import PageInfo, PageResponse

# 2 router: 1 cho Agent (push events), 1 cho phụ huynh (xem)
agent_router = APIRouter(prefix="/api/events", tags=["events-agent"])
parent_router = APIRouter(prefix="/api/events", tags=["events-parent"])


# ==========================================
# Agent gửi events (cần device token)
# ==========================================
@agent_router.post("")
@limiter.limit(RATE_LIMIT_EVENTS)
def push_events(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    device: Device = Depends(__import__("server.routers.devices", fromlist=["require_device"]).require_device),
):
    """Agent đẩy mảng sự kiện lên server.

    Payload:
    {
        "events": [
            {"event_type": "app_start", "app_name": "chrome", "duration_seconds": 0,
             "timestamp": "2024-...", "client_event_id": "uuid-1"},
            ...
        ]
    }
    """
    events = payload.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="'events' phải là list")

    if len(events) > 500:
        raise HTTPException(status_code=400, detail="Tối đa 500 sự kiện / lần gửi")

    # Chuyển string timestamp thành datetime
    for ev in events:
        if isinstance(ev.get("timestamp"), str):
            try:
                ev["timestamp"] = datetime.fromisoformat(ev["timestamp"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"timestamp không hợp lệ: {ev.get('timestamp')}",
                )

    saved = event_service.insert_events(db, device.id, events)
    return {"accepted": saved, "rejected": len(events) - saved}


# ==========================================
# Phụ huynh xem events (cần JWT, có phân trang)
# ==========================================
@parent_router.get("")
def list_events(
    device_id: int = Query(..., description="ID thiết bị"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Item mỗi trang"),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xem các sự kiện của 1 thiết bị (có phân trang)."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    child = db.query(Child).filter(Child.id == device.child_id).first()
    if not child or (child.parent_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Không có quyền")

    offset = (page - 1) * page_size
    items, total = event_service.get_events_paginated(
        db, device_id, offset=offset, limit=page_size, days=days,
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PageResponse(
        items=[{
            "id": e.id,
            "event_type": e.event_type,
            "app_name": e.app_name,
            "domain": e.domain,
            "duration_seconds": e.duration_seconds,
            "timestamp": e.timestamp.isoformat(),
        } for e in items],
        page_info=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
