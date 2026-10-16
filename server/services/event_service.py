"""Service xử lý logic về Event (sự kiện từ Agent)."""

from datetime import datetime, timedelta
from typing import List, Optional
from collections import Counter
from sqlalchemy import func
from sqlalchemy.orm import Session

from server.db.models import Event, Device


def insert_events(db: Session, device_id: int, events: List[dict]) -> int:
    """Chèn nhiều sự kiện cùng lúc, trả về số sự kiện đã lưu.

    Có chống trùng lặp qua client_event_id.

    Args:
        db: session
        device_id: id của thiết bị gửi
        events: list dict, mỗi dict có các key: event_type, app_name, domain,
                duration_seconds, timestamp, client_event_id
    """
    saved = 0
    for ev in events:
        client_id = ev.get("client_event_id")
        # Chống trùng: nếu đã có event với cùng client_event_id thì bỏ qua
        if client_id:
            exists = db.query(Event).filter(
                Event.device_id == device_id,
                Event.client_event_id == client_id,
            ).first()
            if exists:
                continue

        event_obj = Event(
            device_id=device_id,
            event_type=ev["event_type"],
            app_name=ev.get("app_name"),
            domain=ev.get("domain"),
            duration_seconds=ev.get("duration_seconds", 0),
            timestamp=ev["timestamp"],
            client_event_id=client_id,
        )
        db.add(event_obj)
        saved += 1

    db.commit()
    return saved


def get_events_for_device(
    db: Session,
    device_id: int,
    limit: int = 100,
    days: int = 7,
) -> List[Event]:
    """Lấy các sự kiện gần đây của 1 thiết bị (giới hạn limit, không phân trang)."""
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Event)
        .filter(Event.device_id == device_id, Event.timestamp >= since)
        .order_by(Event.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_events_paginated(
    db: Session,
    device_id: int,
    offset: int = 0,
    limit: int = 20,
    days: int = 7,
) -> tuple[List[Event], int]:
    """Lấy events có phân trang (yêu cầu 2.2: phân trang).

    Returns:
        (list_events, total_count)
    """
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(Event).filter(
        Event.device_id == device_id, Event.timestamp >= since,
    )
    total = query.count()
    items = (
        query
        .order_by(Event.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_usage_stats_for_child(
    db: Session,
    child_id: int,
    days: int = 7,
) -> dict:
    """NT5: Con xem được thống kê sử dụng của mình.

    Returns:
        Dict với:
        - top_apps: top 5 app dùng nhiều nhất
        - top_domains: top 5 domain truy cập nhiều nhất
        - blocked_count: số lần bị chặn
        - total_minutes: tổng phút dùng máy
    """
    # Lấy tất cả device của trẻ
    device_ids = [
        d.id for d in db.query(Device.id).filter(Device.child_id == child_id).all()
    ]
    if not device_ids:
        return {
            "top_apps": [],
            "top_domains": [],
            "blocked_count": 0,
            "total_minutes": 0,
        }

    since = datetime.utcnow() - timedelta(days=days)

    # Top apps
    top_apps = (
        db.query(
            Event.app_name,
            func.sum(Event.duration_seconds).label("total_seconds"),
        )
        .filter(
            Event.device_id.in_(device_ids),
            Event.timestamp >= since,
            Event.app_name.isnot(None),
        )
        .group_by(Event.app_name)
        .order_by(func.sum(Event.duration_seconds).desc())
        .limit(5)
        .all()
    )

    # Top domains
    top_domains = (
        db.query(
            Event.domain,
            func.count(Event.id).label("count"),
        )
        .filter(
            Event.device_id.in_(device_ids),
            Event.timestamp >= since,
            Event.domain.isnot(None),
        )
        .group_by(Event.domain)
        .order_by(func.count(Event.id).desc())
        .limit(5)
        .all()
    )

    # Blocked count
    blocked = (
        db.query(Event)
        .filter(
            Event.device_id.in_(device_ids),
            Event.timestamp >= since,
            Event.event_type.in_(["app_blocked", "web_blocked"]),
        )
        .count()
    )

    # Total minutes
    total_seconds = (
        db.query(func.sum(Event.duration_seconds))
        .filter(
            Event.device_id.in_(device_ids),
            Event.timestamp >= since,
            Event.event_type == "session_end",
        )
        .scalar() or 0
    )

    return {
        "top_apps": [
            {"name": r.app_name, "minutes": round(r.total_seconds / 60, 1)}
            for r in top_apps
        ],
        "top_domains": [{"name": r.domain, "visits": r.count} for r in top_domains],
        "blocked_count": blocked,
        "total_minutes": round(total_seconds / 60, 1),
    }


def get_top_apps(db: Session, device_id: int, days: int = 7, limit: int = 10) -> List[dict]:
    """Thống kê top ứng dụng được dùng nhiều nhất."""
    since = datetime.utcnow() - timedelta(days=days)

    results = (
        db.query(
            Event.app_name,
            func.sum(Event.duration_seconds).label("total_seconds"),
            func.count(Event.id).label("count"),
        )
        .filter(
            Event.device_id == device_id,
            Event.timestamp >= since,
            Event.app_name.isnot(None),
        )
        .group_by(Event.app_name)
        .order_by(func.sum(Event.duration_seconds).desc())
        .limit(limit)
        .all()
    )

    return [
        {"name": r.app_name, "minutes": round(r.total_seconds / 60, 1), "count": r.count}
        for r in results
    ]


def get_top_domains(db: Session, device_id: int, days: int = 7, limit: int = 10) -> List[dict]:
    """Thống kê top domain được truy cập nhiều nhất."""
    since = datetime.utcnow() - timedelta(days=days)

    results = (
        db.query(
            Event.domain,
            func.count(Event.id).label("count"),
        )
        .filter(
            Event.device_id == device_id,
            Event.timestamp >= since,
            Event.domain.isnot(None),
        )
        .group_by(Event.domain)
        .order_by(func.count(Event.id).desc())
        .limit(limit)
        .all()
    )

    return [{"name": r.domain, "visits": r.count} for r in results]


def count_blocked_events(db: Session, device_id: int, days: int = 7) -> int:
    """Đếm số lần bị chặn trong khoảng thời gian."""
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Event)
        .filter(
            Event.device_id == device_id,
            Event.timestamp >= since,
            Event.event_type.in_(["app_blocked", "web_blocked"]),
        )
        .count()
    )
