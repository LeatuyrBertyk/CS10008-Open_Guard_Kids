"""Xác thực JWT và quản lý mật khẩu.

Luồng hoạt động:
1. User gửi username + password lên /api/auth/login
2. Server kiểm tra bằng bcrypt
3. Server sinh JWT token, trả về cho client
4. Mọi request sau client gửi kèm header: Authorization: Bearer <token>
5. Server giải mã token để biết user là ai
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from server.db.session import get_db
from server.db.models import User
from server.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRES_HOURS, BCRYPT_ROUNDS


# OAuth2 scheme - FastAPI dùng cái này để tự động lấy token từ header
# tokenUrl là endpoint để lấy token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ==========================================
# Hàm về mật khẩu
# ==========================================
def hash_password(plain_password: str) -> str:
    """Hash mật khẩu bằng bcrypt.

    Args:
        plain_password: mật khẩu gốc (chưa mã hóa)

    Returns:
        Chuỗi hash dạng '$2b$12$...' an toàn để lưu DB
    """
    # Mã hóa password thành bytes, salt tự sinh
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu gốc có khớp với hash không.

    Args:
        plain_password: mật khẩu người dùng nhập
        hashed_password: hash lưu trong DB

    Returns:
        True nếu khớp, False nếu sai
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ==========================================
# Hàm về JWT
# ==========================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT token.

    Args:
        data: thông tin muốn mã hóa vào token, thường là {"sub": username}
        expires_delta: thời gian hết hạn (mặc định dùng JWT_EXPIRES_HOURS)

    Returns:
        Chuỗi token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Giải mã JWT token.

    Args:
        token: chuỗi JWT

    Returns:
        Dict chứa payload nếu hợp lệ, None nếu không hợp lệ / hết hạn
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ==========================================
# Dependency cho FastAPI
# ==========================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Lấy user hiện tại từ JWT token trong header.

    Sử dụng:
        @app.get("/api/me")
        def me(user: User = Depends(get_current_user)):
            return {"username": user.username}

    Raises:
        HTTPException 401 nếu token không hợp lệ hoặc user không tồn tại
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_client_ip(request: Request) -> str:
    """Lấy IP của client, xử lý cả khi qua proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
