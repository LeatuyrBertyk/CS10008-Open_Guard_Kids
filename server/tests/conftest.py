"""Pytest fixtures chung cho server tests.

Mỗi test tự tạo data riêng trong cùng 1 SQLite file tạm.
Đơn giản, đáng tin cậy, không cần del module.
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Tạo database file tạm thời cho mỗi test."""
    db_file = tmp_path / "test.db"
    test_db_url = f"sqlite:///{db_file}"

    # Patch URL trong cả config và session
    from server import config
    monkeypatch.setattr(config, "DATABASE_URL", test_db_url)
    monkeypatch.setattr(config, "DB_PATH", db_file)

    from server.db import session as db_session
    monkeypatch.setattr(db_session, "DATABASE_URL", test_db_url)

    # Tạo engine mới với file test
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from server.db.session import Base
    # Import models để register với Base
    from server.db import models  # noqa: F401

    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)  # đảm bảo sạch
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine)

    # Patch SessionLocal và engine
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)
    monkeypatch.setattr(db_session, "engine", engine)

    yield TestingSession, engine

    engine.dispose()


@pytest.fixture
def client(temp_db):
    """Tạo FastAPI test client với DB tạm."""
    TestingSession, engine = temp_db

    from fastapi.testclient import TestClient
    from server.main import app
    from server.db import session as db_session

    def override_get_db():
        try:
            db = TestingSession()
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_session.get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
