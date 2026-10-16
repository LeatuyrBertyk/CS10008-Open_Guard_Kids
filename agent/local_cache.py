"""SQLite local cache - lưu sự kiện khi mất mạng.

Khi Agent không gọi được server (mất mạng, server down), sự kiện
được ghi vào SQLite local. Khi mạng trở lại, sẽ flush lên server.

Dùng SQLite (không phải JSON file) vì:
- Ghi nhanh, không block main thread
- An toàn khi bị tắt đột ngột
- Dễ query: lấy N sự kiện cũ nhất
"""

import sqlite3
import json
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from shared.constants import (
    AGENT_LOCAL_DB,
    MAX_LOCAL_EVENTS,
    EVENT_FLUSH_BATCH_SIZE,
)

logger = logging.getLogger("ogk.agent.cache")

# Đường dẫn file DB local
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / AGENT_LOCAL_DB


class LocalCache:
    """Cache local cho events và state."""

    def __init__(self, db_path: Optional[Path] = None):
        """Khởi tạo cache.

        Args:
            db_path: đường dẫn file .db, mặc định dùng AGENT_LOCAL_DB
        """
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Tạo bảng nếu chưa có."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pending_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        app_name TEXT,
                        domain TEXT,
                        duration_seconds INTEGER DEFAULT 0,
                        timestamp TEXT NOT NULL,
                        client_event_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        sent INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_sent
                    ON pending_events(sent, id)
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_state (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    # ==========================================
    # Events
    # ==========================================
    def save_event(
        self,
        event_type: str,
        timestamp: datetime,
        app_name: Optional[str] = None,
        domain: Optional[str] = None,
        duration_seconds: int = 0,
        client_event_id: Optional[str] = None,
    ) -> int:
        """Lưu 1 sự kiện vào cache local.

        Returns:
            ID của event vừa lưu
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                # Nếu quá nhiều event chưa gửi, xóa bớt cũ nhất
                self._cleanup_if_needed(conn)

                cur = conn.execute(
                    """INSERT INTO pending_events
                       (event_type, app_name, domain, duration_seconds, timestamp, client_event_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        event_type,
                        app_name,
                        domain,
                        duration_seconds,
                        timestamp.isoformat(),
                        client_event_id,
                    ),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def get_pending_events(self, limit: int = EVENT_FLUSH_BATCH_SIZE) -> List[Dict[str, Any]]:
        """Lấy các sự kiện chưa gửi (cũ nhất trước)."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """SELECT * FROM pending_events
                       WHERE sent = 0
                       ORDER BY id ASC
                       LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def mark_sent(self, ids: List[int]):
        """Đánh dấu các event đã gửi thành công lên server."""
        if not ids:
            return
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                placeholders = ",".join("?" * len(ids))
                conn.execute(
                    f"UPDATE pending_events SET sent = 1 WHERE id IN ({placeholders})",
                    ids,
                )
                conn.commit()
            finally:
                conn.close()

    def delete_sent_events(self):
        """Xóa các event đã gửi để giảm dung lượng DB."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("DELETE FROM pending_events WHERE sent = 1")
                conn.commit()
            finally:
                conn.close()

    def _cleanup_if_needed(self, conn: sqlite3.Connection):
        """Nếu số event chưa gửi vượt quá MAX_LOCAL_EVENTS, xóa bớt cũ nhất."""
        count = conn.execute(
            "SELECT COUNT(*) FROM pending_events WHERE sent = 0"
        ).fetchone()[0]
        if count >= MAX_LOCAL_EVENTS:
            # Xóa 10% cũ nhất
            to_delete = MAX_LOCAL_EVENTS // 10
            conn.execute(
                """DELETE FROM pending_events WHERE id IN (
                    SELECT id FROM pending_events WHERE sent = 0 ORDER BY id ASC LIMIT ?
                )""",
                (to_delete,),
            )
            logger.warning(f"Local cache đầy, đã xóa {to_delete} event cũ nhất")

    def count_pending(self) -> int:
        """Đếm số event chưa gửi."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                return conn.execute(
                    "SELECT COUNT(*) FROM pending_events WHERE sent = 0"
                ).fetchone()[0]
            finally:
                conn.close()

    # ==========================================
    # State (key-value)
    # ==========================================
    def set_state(self, key: str, value: Any):
        """Lưu state (key-value), value sẽ được JSON serialize."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)""",
                    (key, json.dumps(value)),
                )
                conn.commit()
            finally:
                conn.close()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Đọc state."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                row = conn.execute(
                    "SELECT value FROM app_state WHERE key = ?", (key,)
                ).fetchone()
                if row is None:
                    return default
                return json.loads(row[0])
            except Exception:
                return default
            finally:
                conn.close()

    # ==========================================
    # Screen time
    # ==========================================
    def get_usage_today(self) -> int:
        """Lấy số phút đã dùng hôm nay (tính từ lần reset gần nhất)."""
        state = self.get_state("usage_today", {"date": "", "minutes": 0})
        today = datetime.now().strftime("%Y-%m-%d")
        if state.get("date") != today:
            # Ngày mới, reset về 0
            self.set_state("usage_today", {"date": today, "minutes": 0})
            return 0
        return int(state.get("minutes", 0))

    def add_usage_minutes(self, minutes: int):
        """Cộng thêm số phút đã dùng."""
        today = datetime.now().strftime("%Y-%m-%d")
        state = self.get_state("usage_today", {"date": today, "minutes": 0})
        if state.get("date") != today:
            state = {"date": today, "minutes": 0}
        state["minutes"] = int(state.get("minutes", 0)) + minutes
        self.set_state("usage_today", state)
