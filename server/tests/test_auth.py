"""Test cho authentication: login, JWT, password.

Mỗi test tự tạo user riêng (DB trống ban đầu).
"""

import pytest


def _create_admin(TestingSession, username="admin", password="admin123"):
    """Helper: tạo user admin mới."""
    from server.db.models import User
    import bcrypt
    from server.config import BCRYPT_ROUNDS
    db = TestingSession()
    try:
        user = User(
            username=username,
            password_hash=bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            ).decode("utf-8"),
            role="admin",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def test_login_success(client, temp_db):
    """Đăng nhập thành công với admin/admin123."""
    _create_admin(temp_db[0])

    resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


def test_login_wrong_password(client, temp_db):
    """Đăng nhập sai mật khẩu → 401."""
    _create_admin(temp_db[0])

    resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    """Đăng nhập user không tồn tại → 401."""
    resp = client.post(
        "/api/auth/login",
        data={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    """GET /api/auth/me cần token."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, temp_db):
    """GET /api/auth/me với token hợp lệ."""
    _create_admin(temp_db[0])

    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"


def test_me_invalid_token(client):
    """Token không hợp lệ → 401."""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert resp.status_code == 401
