"""Test cho events: gửi từ Agent, xem từ dashboard."""

import pytest
from datetime import datetime


def _create_device(TestingSession, child_name="C", token="test-token"):
    """Tạo user + child + device, trả về token."""
    import bcrypt
    from server.config import BCRYPT_ROUNDS
    from server.db.models import User, Child, Device
    db = TestingSession()
    try:
        admin = User(
            username="admin",
            password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        child = Child(parent_id=admin.id, name=child_name)
        db.add(child)
        db.commit()
        device = Device(
            child_id=child.id,
            hostname="H",
            token_hash=bcrypt.hashpw(
                token.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            ).decode("utf-8"),
        )
        db.add(device)
        db.commit()
        return token
    finally:
        db.close()


def test_push_events(client, temp_db):
    """Agent đẩy danh sách events."""
    TestingSession, _ = temp_db
    _create_device(TestingSession)

    resp = client.post(
        "/api/events",
        json={
            "events": [
                {
                    "event_type": "app_start",
                    "app_name": "chrome",
                    "duration_seconds": 0,
                    "timestamp": datetime.now().isoformat(),
                    "client_event_id": "test-1",
                },
            ]
        },
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1


def test_push_events_dedup(client, temp_db):
    """Events trùng client_event_id bị bỏ qua."""
    TestingSession, _ = temp_db
    _create_device(TestingSession)

    payload = {
        "events": [
            {
                "event_type": "app_start",
                "app_name": "chrome",
                "duration_seconds": 0,
                "timestamp": datetime.now().isoformat(),
                "client_event_id": "duplicate-id",
            }
        ]
    }
    r1 = client.post("/api/events", json=payload, headers={"Authorization": "Bearer test-token"})
    r2 = client.post("/api/events", json=payload, headers={"Authorization": "Bearer test-token"})
    assert r1.json()["accepted"] == 1
    assert r2.json()["accepted"] == 0
    assert r2.json()["rejected"] == 1


def test_push_events_multiple(client, temp_db):
    """Đẩy nhiều events cùng lúc."""
    TestingSession, _ = temp_db
    _create_device(TestingSession)

    events = [
        {
            "event_type": "app_start",
            "app_name": f"app{i}",
            "duration_seconds": 0,
            "timestamp": datetime.now().isoformat(),
            "client_event_id": f"e{i}",
        }
        for i in range(5)
    ]
    resp = client.post(
        "/api/events",
        json={"events": events},
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 5


def test_push_events_too_many(client, temp_db):
    """Đẩy quá 500 events → 400."""
    TestingSession, _ = temp_db
    _create_device(TestingSession)

    events = [
        {
            "event_type": "app_start",
            "app_name": "x",
            "duration_seconds": 0,
            "timestamp": datetime.now().isoformat(),
            "client_event_id": f"e{i}",
        }
        for i in range(501)
    ]
    resp = client.post(
        "/api/events",
        json={"events": events},
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 400


def test_push_events_without_token(client):
    """Không có token → 401."""
    resp = client.post("/api/events", json={"events": []})
    assert resp.status_code == 401
