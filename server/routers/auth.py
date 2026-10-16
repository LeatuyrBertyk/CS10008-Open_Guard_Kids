"""Router xử lý xác thực: login, lấy thông tin user.

Tích hợp rate limiting chống brute-force.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.db.models import User
from server.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    get_client_ip,
)
from server.services.audit_service import log_action
from server.config import JWT_EXPIRES_HOURS
from server.rate_limiter import limiter
from shared.constants import RATE_LIMIT_LOGIN, RATE_LIMIT_AUTH_ME

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
@limiter.limit(RATE_LIMIT_LOGIN)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Đăng nhập bằng username + password, trả về JWT token.

    Form data (application/x-www-form-urlencoded):
    - username
    - password
    """
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        # Ghi log đăng nhập thất bại (nếu user tồn tại)
        if user:
            log_action(
                db,
                username=user.username,
                action="login_failed",
                ip_address=get_client_ip(request),
                user_id=user.id,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    # Tạo token
    access_token = create_access_token(
        data={"sub": user.username, "uid": user.id, "role": user.role},
        expires_delta=timedelta(hours=JWT_EXPIRES_HOURS),
    )

    # Ghi log đăng nhập thành công
    log_action(
        db,
        username=user.username,
        action="login_success",
        ip_address=get_client_ip(request),
        user_id=user.id,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRES_HOURS * 3600,
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại (cần token)."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }
