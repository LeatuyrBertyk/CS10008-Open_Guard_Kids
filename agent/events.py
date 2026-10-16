"""Module quản lý hàng đợi sự kiện + flush lên server.

Sự kiện được tạo ra liên tục (mở app, vào web...). Thay vì gửi
ngay từng cái lên server (tốn network), ta gom vào hàng đợi và
flush theo định kỳ.
"""

import threading
import time
import logging
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from shared.constants import EVENT_FLUSH_INTERVAL_SECONDS
from agent.local_cache import LocalCache
from agent.client import ServerClient

logger = logging.getLogger("ogk.agent.events")


class EventQueue:
    """Hàng đợi sự kiện: ghi local + flush lên server định kỳ."""

    def __init__(self, cache: LocalCache, client: ServerClient):
        self.cache = cache
        self.client = client
        self._stop_event = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None

    def start(self):
        """Khởi động thread flush định kỳ."""
        if self._flush_thread and self._flush_thread.is_alive():
            return
        self._stop_event.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info("EventQueue started")

    def stop(self):
        """Dừng thread flush."""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        logger.info("EventQueue stopped")

    def record(
        self,
        event_type: str,
        app_name: Optional[str] = None,
        domain: Optional[str] = None,
        duration_seconds: int = 0,
        timestamp: Optional[datetime] = None,
    ):
        """Ghi 1 sự kiện vào hàng đợi (sẽ flush lên server sau).

        Args:
            event_type: loại sự kiện (app_start, web_visit, app_blocked, ...)
            app_name: tên process (vd 'chrome')
            domain: tên miền (vd 'facebook.com')
            duration_seconds: thời lượng
            timestamp: thời điểm xảy ra (mặc định: now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Mỗi event có 1 client_event_id duy nhất (chống trùng khi retry)
        client_id = f"{int(timestamp.timestamp() * 1000)}-{uuid4().hex[:8]}"

        self.cache.save_event(
            event_type=event_type,
            timestamp=timestamp,
            app_name=app_name,
            domain=domain,
            duration_seconds=duration_seconds,
            client_event_id=client_id,
        )

    def record_app_start(self, app_name: str):
        """Ghi sự kiện mở app."""
        self.record("app_start", app_name=app_name)

    def record_app_end(self, app_name: str, duration_seconds: int):
        """Ghi sự kiện đóng app."""
        self.record("app_end", app_name=app_name, duration_seconds=duration_seconds)

    def record_app_blocked(self, app_name: str):
        """Ghi sự kiện app bị chặn."""
        self.record("app_blocked", app_name=app_name)

    def record_web_visit(self, domain: str):
        """Ghi sự kiện vào web."""
        self.record("web_visit", domain=domain)

    def record_web_blocked(self, domain: str):
        """Ghi sự kiện web bị chặn."""
        self.record("web_blocked", domain=domain)

    def _flush_loop(self):
        """Vòng lặp flush: mỗi EVENT_FLUSH_INTERVAL_SECONDS thử gửi 1 lần."""
        while not self._stop_event.is_set():
            try:
                self._flush_once()
            except Exception as e:
                logger.error(f"Lỗi flush events: {e}")
            self._stop_event.wait(EVENT_FLUSH_INTERVAL_SECONDS)

    def _flush_once(self):
        """Gửi 1 batch events lên server (nếu có)."""
        pending = self.cache.get_pending_events()
        if not pending:
            return

        # Chuyển timestamp string -> datetime
        for ev in pending:
            try:
                ev["timestamp"] = datetime.fromisoformat(ev["timestamp"])
            except Exception:
                ev["timestamp"] = datetime.now()

        try:
            result = self.client.push_events(pending)
            # Đánh dấu các event đã gửi thành công
            self.cache.mark_sent([e["id"] for e in pending])
            logger.info(
                f"Flushed {result.get('accepted', 0)} events "
                f"({result.get('rejected', 0)} rejected)"
            )
        except Exception as e:
            logger.warning(f"Không flush được events: {e}")

    def flush_now(self):
        """Flush ngay lập tức (gọi trước khi thoát)."""
        try:
            self._flush_once()
            self.cache.delete_sent_events()
        except Exception as e:
            logger.error(f"Flush trước khi thoát lỗi: {e}")
