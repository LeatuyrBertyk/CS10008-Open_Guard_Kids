"""Cấu hình cho Server.

Đọc các giá trị từ biến môi trường nếu có, ngược lại dùng giá trị mặc định.
Điều này giúp dễ dàng chuyển đổi giữa môi trường dev/prod.
"""

import os
from pathlib import Path

from shared.constants import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SERVER_DB_FILE,
)


# ==========================================
# Đường dẫn
# ==========================================
# Thư mục gốc của project (nơi chứa folder server/, agent/, shared/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Đường dẫn file database
DB_PATH = PROJECT_ROOT / SERVER_DB_FILE


# ==========================================
# Cấu hình Database
# ==========================================
# URL kết nối SQLite - dùng đường dẫn tuyệt đối để tránh lỗi
# 3 dấu gạch chéo (sqlite:///) cho đường dẫn tương đối,
# cần thêm / nữa cho tuyệt đối trên Unix.
# Trên Windows, đường dẫn là C:\..., cần dùng dấu /
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"


# ==========================================
# Cấu hình JWT (JSON Web Token)
# ==========================================
# Khóa bí mật để ký token. Trong production phải đặt qua biến môi trường!
# Tạo key mạnh: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET = os.environ.get("OGK_JWT_SECRET", "CHANGE_ME_IN_PRODUCTION_ogk_dev_secret_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 24  # Token hết hạn sau 24 giờ


# ==========================================
# Cấu hình Server
# ==========================================
SERVER_HOST = os.environ.get("OGK_SERVER_HOST", DEFAULT_SERVER_HOST)
SERVER_PORT = int(os.environ.get("OGK_SERVER_PORT", DEFAULT_SERVER_PORT))

# Có dùng HTTPS không (cho demo thì False, production thì True)
USE_HTTPS = os.environ.get("OGK_USE_HTTPS", "false").lower() == "true"

# Đường dẫn chứng chỉ TLS (chỉ dùng khi USE_HTTPS=True)
SSL_CERTFILE = os.environ.get("OGK_SSL_CERT", str(PROJECT_ROOT / "certs" / "cert.pem"))
SSL_KEYFILE = os.environ.get("OGK_SSL_KEY", str(PROJECT_ROOT / "certs" / "key.pem"))


# ==========================================
# Cấu hình mật khẩu
# ==========================================
# Vòng lặp bcrypt - 12 là cân bằng giữa tốc độ và bảo mật
BCRYPT_ROUNDS = 12


# ==========================================
# Cấu hình mặc định cho user admin đầu tiên
# ==========================================
# Khi init_db.py chạy lần đầu, nó sẽ tạo user này nếu chưa tồn tại
DEFAULT_ADMIN_USERNAME = os.environ.get("OGK_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("OGK_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_FULLNAME = "Quản trị viên"


# ==========================================
# Hàm tiện ích
# ==========================================
def is_production() -> bool:
    """Kiểm tra có đang chạy ở chế độ production không."""
    return os.environ.get("OGK_ENV", "development") == "production"


def print_config() -> None:
    """In cấu hình hiện tại ra console (dùng khi debug)."""
    # Tắt encoding lỗi trên Windows console với ký tự Unicode
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print(f"{'OGK Server Configuration':^60}")
    print("=" * 60)
    print(f"  Project root:  {PROJECT_ROOT}")
    print(f"  Database:      {DATABASE_URL}")
    print(f"  Server:        {SERVER_HOST}:{SERVER_PORT}")
    print(f"  HTTPS:         {USE_HTTPS}")
    print(f"  Environment:   {'production' if is_production() else 'development'}")
    print(f"  Admin user:    {DEFAULT_ADMIN_USERNAME}")
    print("=" * 60)
