"""Khởi tạo database: tạo bảng + user admin mặc định.

Chạy lệnh:
    python -m server.db.init_db
"""

import sys
import secrets
from pathlib import Path

# Thêm project root vào sys.path để import được các module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bcrypt

from server.db.session import engine, Base, SessionLocal
from server.db.models import User, Child, Device, Policy
from server.config import (
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_FULLNAME,
    print_config,
    DB_PATH,
    BCRYPT_ROUNDS,
)


def create_all_tables() -> None:
    """Tạo tất cả bảng trong database (nếu chưa tồn tại)."""
    print("[1/3] Tạo bảng...")
    Base.metadata.create_all(bind=engine)
    print(f"      OK - database: {DB_PATH}")


def create_default_admin() -> None:
    """Tạo user admin mặc định nếu chưa có user nào."""
    print("[2/3] Tạo user admin...")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        if existing:
            print(f"      Bỏ qua - user '{DEFAULT_ADMIN_USERNAME}' đã tồn tại")
            return

        # Hash mật khẩu bằng bcrypt
        password_hash = bcrypt.hashpw(
            DEFAULT_ADMIN_PASSWORD.encode("utf-8"),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode("utf-8")

        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=password_hash,
            full_name=DEFAULT_ADMIN_FULLNAME,
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"      OK - user: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
    finally:
        db.close()


def create_demo_data() -> None:
    """Tạo dữ liệu mẫu để demo (1 child + 1 device + 1 policy)."""
    print("[3/3] Tạo dữ liệu mẫu...")
    db = SessionLocal()
    try:
        # Chỉ tạo nếu chưa có child nào
        if db.query(Child).count() > 0:
            print("      Bỏ qua - đã có dữ liệu")
            return

        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            print("      Bỏ qua - chưa có admin")
            return

        # Tạo 1 child mẫu
        child = Child(
            parent_id=admin.id,
            name="Nguyễn Văn An (demo)",
            birth_year=2012,
            notes="Học sinh lớp 7 - dữ liệu mẫu để test"
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        # Tạo 1 device mẫu
        device = Device(
            child_id=child.id,
            hostname="LAPTOP-DEMO",
            os_version="Windows 11 Pro 23H2",
            mac_address="AA:BB:CC:DD:EE:FF",
            # Token demo - trong thực tế sẽ sinh ngẫu nhiên khi enroll
            token_hash=bcrypt.hashpw(
                b"demo-device-token-12345",
                bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
            ).decode("utf-8"),
            is_active=True,
        )
        db.add(device)
        db.commit()
        db.refresh(device)

        # Tạo policy mặc định
        policy = Policy(
            device_id=device.id,
            max_minutes_per_day=120,  # 2 tiếng/ngày
            blocked_apps=["steam", "discord", "riotclient"],
            blocked_domains=["facebook.com", "tiktok.com"],
            allowed_domains=[],
            schedule={
                "mon": [{"start": "19:00", "end": "21:00"}],
                "tue": [{"start": "19:00", "end": "21:00"}],
                "wed": [{"start": "19:00", "end": "21:00"}],
                "thu": [{"start": "19:00", "end": "21:00"}],
                "fri": [{"start": "19:00", "end": "22:00"}],
                "sat": [{"start": "14:00", "end": "22:00"}],
                "sun": [{"start": "14:00", "end": "22:00"}],
            },
            bedtime_start="22:00",
            bedtime_end="06:00",
        )
        db.add(policy)
        db.commit()

        # Tạo mã enroll để dễ test (in ra console)
        demo_enroll_code = "DEMO2024"
        print(f"      OK - child: {child.name}")
        print(f"      OK - device: {device.hostname}")
        print(f"      OK - enroll code demo: {demo_enroll_code}")
        print(f"      OK - device token demo: demo-device-token-12345")
    finally:
        db.close()


def main() -> None:
    """Hàm main: chạy tất cả bước khởi tạo."""
    print()
    print_config()
    print()

    # Tạo thư mục chứa database nếu chưa có
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    create_all_tables()
    create_default_admin()
    create_demo_data()

    print()
    print("=" * 60)
    print("Khởi tạo database HOÀN TẤT!")
    print("=" * 60)
    print(f"  Đăng nhập:  username = '{DEFAULT_ADMIN_USERNAME}'")
    print(f"              password = '{DEFAULT_ADMIN_PASSWORD}'")
    print(f"  Database:   {DB_PATH}")
    print("  Chạy server: uvicorn server.main:app --reload")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
