"""Module đếm thời gian sử dụng máy (screen time).

Logic:
- Mỗi SCREENTIME_CHECK_INTERVAL giây, kiểm tra session có active không
- Nếu active (có thao tác chuột/bàn phím gần đây) → cộng thời gian
- So sánh với max_minutes_per_day trong policy
- Nếu vượt quá → trigger callback để khóa máy
"""

import threading
import time
import logging
from typing import Optional, Callable

from shared.constants import SCREENTIME_CHECK_INTERVAL, IDLE_THRESHOLD_SECONDS
from agent.local_cache import LocalCache

logger = logging.getLogger("ogk.agent.screentime")


class ScreenTimeCounter:
    """Đếm thời gian sử dụng máy."""

    def __init__(
        self,
        cache: LocalCache,
        on_limit_exceeded: Optional[Callable[[], None]] = None,
    ):
        self.cache = cache
        self.on_limit_exceeded = on_limit_exceeded
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._max_minutes_per_day = 120  # sẽ được cập nhật từ policy
        self._last_check_time: Optional[float] = None

    def set_limit(self, max_minutes: int):
        """Cập nhật giới hạn thời gian (từ policy)."""
        self._max_minutes_per_day = int(max_minutes)
        logger.info(f"Screen time limit set to {max_minutes} min/day")

    def start(self):
        """Khởi động thread đếm."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._last_check_time = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("ScreenTimeCounter started")

    def stop(self):
        """Dừng thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ScreenTimeCounter stopped")

    def _loop(self):
        """Vòng lặp chính: mỗi SCREENTIME_CHECK_INTERVAL giây."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Lỗi screen time: {e}")
            self._stop_event.wait(SCREENTIME_CHECK_INTERVAL)

    def _tick(self):
        """Xử lý 1 lần kiểm tra."""
        now = time.time()
        if self._last_check_time is None:
            self._last_check_time = now
            return

        elapsed = now - self._last_check_time
        self._last_check_time = now

        # Tính số giây session active (gộp thành phút sau)
        # Trong production: dùng psutil để kiểm tra input activity
        # Ở đây đơn giản: nếu elapsed < IDLE_THRESHOLD thì tính là active
        if elapsed < IDLE_THRESHOLD_SECONDS:
            # Cộng thời gian dùng (làm tròn xuống phút)
            minutes_to_add = int(elapsed // 60)
            if minutes_to_add > 0:
                self.cache.add_usage_minutes(minutes_to_add)

        # Kiểm tra giới hạn
        used = self.cache.get_usage_today()
        if used >= self._max_minutes_per_day:
            is_locked = self.cache.get_state("is_locked", False)
            if not is_locked:
                logger.warning(f"Đã dùng {used}/{self._max_minutes_per_day} phút - VƯỢT GIỚI HẠN")
                self.cache.set_state("is_locked", True)
                if self.on_limit_exceeded:
                    self.on_limit_exceeded()

    def get_minutes_used_today(self) -> int:
        """Lấy số phút đã dùng hôm nay."""
        return self.cache.get_usage_today()

    def get_minutes_remaining(self) -> int:
        """Lấy số phút còn lại trong ngày."""
        used = self.get_minutes_used_today()
        return max(0, self._max_minutes_per_day - used)
