"""Module heartbeat: gửi tín hiệu "tôi vẫn sống" lên server mỗi 60s.

Đồng thời nhận policy mới (nếu phụ huynh vừa thay đổi) và lệnh
force_lock (nếu hết giờ).
"""

import threading
import time
import logging
from typing import Optional, Callable

from shared.constants import HEARTBEAT_INTERVAL_SECONDS
from agent.client import ServerClient
from agent.local_cache import LocalCache

logger = logging.getLogger("ogk.agent.heartbeat")


class HeartbeatThread:
    """Thread chạy nền, gọi heartbeat mỗi HEARTBEAT_INTERVAL_SECONDS."""

    def __init__(
        self,
        client: ServerClient,
        cache: LocalCache,
        on_policy_update: Optional[Callable[[dict], None]] = None,
        on_force_lock: Optional[Callable[[], None]] = None,
    ):
        """Khởi tạo.

        Args:
            client: ServerClient
            cache: LocalCache (để lấy usage_today và pending count)
            on_policy_update: callback khi nhận policy mới
            on_force_lock: callback khi server yêu cầu khóa máy
        """
        self.client = client
        self.cache = cache
        self.on_policy_update = on_policy_update
        self.on_force_lock = on_force_lock
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current_policy: dict = {}

    def set_current_policy(self, policy: dict):
        """Cập nhật policy hiện tại (để so sánh)."""
        self._current_policy = policy

    def start(self):
        """Khởi động thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Heartbeat started (interval={HEARTBEAT_INTERVAL_SECONDS}s)")

    def stop(self):
        """Dừng thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat stopped")

    def _loop(self):
        """Vòng lặp chính."""
        while not self._stop_event.is_set():
            try:
                self._send_once()
            except Exception as e:
                logger.error(f"Lỗi heartbeat: {e}")
            self._stop_event.wait(HEARTBEAT_INTERVAL_SECONDS)

    def _send_once(self):
        """Gửi 1 lần heartbeat và xử lý response."""
        usage = self.cache.get_usage_today()
        pending = self.cache.count_pending()
        is_locked = self.cache.get_state("is_locked", False)

        try:
            result = self.client.heartbeat(
                usage_minutes_today=usage,
                is_locked=is_locked,
                pending_events_count=pending,
            )
        except Exception as e:
            logger.warning(f"Heartbeat thất bại: {e}")
            return

        logger.debug(f"Heartbeat OK: usage={usage}min, pending={pending}")

        # Xử lý policy update
        if result.get("new_policy"):
            new_pol = result["new_policy"]
            if new_pol != self._current_policy:
                logger.info("Nhận policy mới từ server")
                self._current_policy = new_pol
                self.cache.set_state("current_policy", new_pol)
                if self.on_policy_update:
                    self.on_policy_update(new_pol)

        # Xử lý force lock
        if result.get("force_lock") and not is_locked:
            logger.warning("Server yêu cầu khóa máy")
            self.cache.set_state("is_locked", True)
            if self.on_force_lock:
                self.on_force_lock()

    def send_once_sync(self):
        """Gửi heartbeat 1 lần (không qua thread) - dùng khi cần test."""
        self._send_once()
