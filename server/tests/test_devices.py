"""Test cho device endpoints: enroll, heartbeat."""

import pytest
from sqlalchemy.orm import sessionmaker


def _create_full_setup(engine):
    """Tạo user admin + child, trả về dict thông tin."""
    import bcrypt
    from server.config import BCRYPT_ROUNDS
    from server.db.models import User, Child, Device, Policy
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        admin = User(
            username="admin",
            password_hash=bcrypt.hashpw(
                b"admin123", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            ).decode("utf-8"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        child = Child(parent_id=admin.id, name="Test Child")
        db.add(child)
        db.commit()
        db.refresh(child)

        policy = Policy(
            device_id=0,  # sẽ update sau
            max_minutes_per_day=120,
        )
        db.add(policy)
        db.commit()
        return {"child_id": child.id, "admin_id": admin.id, "policy_id": policy.id}
    finally:
        db.close()


def _create_device_with_token(engine, child_id, hostname="TEST-PC", token="test-device-token"):
    """Tạo device với token đã biết, trả về device_id."""
    import bcrypt
    from server.config import BCRYPT_ROUNDS
    from server.db.models import Device
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        device = Device(
            child_id=child_id,
            hostname=hostname,
            os_version="Windows 11",
            token_hash=bcrypt.hashpw(
                token.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            ).decode("utf-8"),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device.id
    finally:
        db.close()


def test_enroll_with_demo_code(client, temp_db):
    """Enroll máy mới với mã DEMO2024."""
    _create_full_setup(temp_db[1])

    resp = client.post("/api/devices/enroll", json={
        "device_code": "DEMO2024",
        "hostname": "TEST-PC",
        "os_version": "Windows 11",
        "mac_address": "AA:BB:CC:DD:EE:FF",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "device_token" in data
    assert "device_id" in data
    assert data["child_name"] == "Test Child"
    assert "policy" in data
    assert data["policy"]["max_minutes_per_day"] == 120


def test_enroll_invalid_code(client, temp_db):
    """Enroll với mã sai → 404."""
    _create_full_setup(temp_db[1])

    resp = client.post("/api/devices/enroll", json={
        "device_code": "WRONG_CODE",
        "hostname": "TEST-PC",
        "os_version": "Windows 11",
    })
    assert resp.status_code == 404


def test_heartbeat_success(client, temp_db):
    """Gửi heartbeat với token hợp lệ."""
    info = _create_full_setup(temp_db[1])
    _create_device_with_token(temp_db[1], info["child_id"], token="test-token-123")

    resp = client.post(
        "/api/devices/heartbeat",
        json={"usage_minutes_today": 30, "is_locked": False, "pending_events_count": 0},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ack"] is True
    assert "new_policy" in data


def test_heartbeat_without_token(client, temp_db):
    """Heartbeat không có token → 401."""
    resp = client.post(
        "/api/devices/heartbeat",
        json={"usage_minutes_today": 30},
    )
    assert resp.status_code == 401


def test_heartbeat_invalid_token(client, temp_db):
    """Heartbeat với token sai → 401."""
    info = _create_full_setup(temp_db[1])
    _create_device_with_token(temp_db[1], info["child_id"], token="real-token")

    resp = client.post(
        "/api/devices/heartbeat",
        json={"usage_minutes_today": 30},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401
