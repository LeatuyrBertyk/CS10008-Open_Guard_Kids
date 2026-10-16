"""Kết nối database SQLite với SQLAlchemy.

Sử dụng:
    from server.db.session import SessionLocal, engine
    db = SessionLocal()
    db.query(User).all()
    db.close()
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from server.config import DATABASE_URL


# ==========================================
# Tạo Engine
# ==========================================
# echo=False: không in SQL ra console (bật True khi debug)
# connect_args={"check_same_thread": False}: SQLite cần cái này để dùng
# trong nhiều thread (vì FastAPI chạy đa luồng).
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# ==========================================
# Bật WAL mode cho SQLite
# ==========================================
# WAL (Write-Ahead Logging) giúp SQLite ghi và đọc cùng lúc mà không block nhau
# Đây là cải tiến quan trọng để server không bị treo khi Agent đang ghi dữ liệu
@event.listens_for(engine, "connect")
def _enable_sqlite_wal(dbapi_connection, connection_record):
    """Bật WAL mode mỗi khi có kết nối mới."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # cân bằng tốc độ/an toàn
    cursor.execute("PRAGMA foreign_keys=ON")      # bật khóa ngoại
    cursor.close()


# ==========================================
# Session factory
# ==========================================
# SessionLocal: tạo session mới cho mỗi request
# autocommit=False: phải gọi db.commit() thủ công
# autoflush=False: tự flush khi query (an toàn hơn)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ==========================================
# Base class cho models
# ==========================================
# Tất cả model kế thừa Base này để SQLAlchemy biết cần tạo bảng
Base = declarative_base()


# ==========================================
# Dependency cho FastAPI
# ==========================================
def get_db():
    """Tạo session cho mỗi request, tự động đóng khi xong.

    Sử dụng trong FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
