"""Module App Controller - chặn ứng dụng bị cấm.

Cách hoạt động:
- Mỗi APP_SCAN_INTERVAL giây, quét danh sách process đang chạy
- Lấy tên process (chrome.exe, steam.exe, ...)
- So sánh với policy.blocked_apps
- Nếu match → kiểm tra allowlist (cho phép gọi khẩn cấp)
- Nếu không có trong allowlist → kết thúc process
- Ghi event app_blocked

Tuân thủ nguyên tắc NT4 (giải thích) và NT6 (an toàn):
- KHÔNG chặn process trong allowlist (vd svchost, msmpeng)
- Trước khi kill, hiển thị thông báo cho con biết lý do
"""

import threading
import time
import logging
from typing import Optional, Callable, List

try:
    import psutil
except ImportError:
    psutil = None

from shared.constants import APP_SCAN_INTERVAL, APP_KILL_GRACE_PERIOD
from shared.allowlist import is_process_allowed
from agent.events import EventQueue

logger = logging.getLogger("ogk.agent.app_controller")


class AppController:
    """Chặn ứng dụng theo policy."""

    def __init__(
        self,
        event_queue: EventQueue,
        on_block_attempt: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            event_queue: EventQueue để ghi sự kiện
            on_block_attempt: callback khi phát hiện app bị chặn,
                              dùng để hiển thị thông báo trên Tray UI
        """
        self.event_queue = event_queue
        self.on_block_attempt = on_block_attempt
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._blocked_apps: List[str] = []  # danh sách từ policy
        self._is_locked = False  # khi True, chặn tất cả app không thiết yếu

    def update_policy(self, blocked_apps: List[str]):
        """Cập nhật danh sách app bị chặn từ policy."""
        # Normalize: lowercase, bỏ .exe
        normalized = []
        for app in blocked_apps:
            app = app.lower().strip()
            if app.endswith(".exe"):
                app = app[:-4]
            if app:
                normalized.append(app)
        self._blocked_apps = normalized
        logger.info(f"Blocked apps updated: {normalized}")

    def set_locked(self, locked: bool):
        """Đặt trạng thái khóa máy (chặn mọi app không thiết yếu)."""
        self._is_locked = locked
        logger.info(f"AppController lock state: {locked}")

    def start(self):
        """Khởi động thread quét."""
        if not psutil:
            logger.warning("psutil chưa cài, AppController không hoạt động")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("AppController started")

    def stop(self):
        """Dừng thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("AppController stopped")

    def _loop(self):
        """Vòng lặp chính: mỗi APP_SCAN_INTERVAL quét 1 lần."""
        while not self._stop_event.is_set():
            try:
                self._scan_once()
            except Exception as e:
                logger.error(f"Lỗi scan: {e}")
            self._stop_event.wait(APP_SCAN_INTERVAL)

    def _scan_once(self):
        """Quét 1 lần, kill các app vi phạm."""
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                name = proc.info["name"]
                if not name:
                    continue
                if self._should_block(name):
                    self._block_process(proc, name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _should_block(self, process_name: str) -> bool:
        """Kiểm tra process có nên bị chặn không."""
        # Luôn cho phép các process trong allowlist
        if is_process_allowed(process_name):
            return False

        name = process_name.lower().strip()
        if name.endswith(".exe"):
            name = name[:-4]

        # Nếu đang lock máy, chặn mọi app không thiết yếu
        if self._is_locked:
            # Chỉ cho phép process thiết yếu (allowlist đã xử lý ở trên)
            return True

        # Nếu không lock, chỉ chặn app trong danh sách
        return name in self._blocked_apps

    def _block_process(self, proc, name: str):
        """Kết thúc 1 process vi phạm."""
        try:
            logger.info(f"Killing process: {name} (pid={proc.pid})")
            # Ghi sự kiện
            self.event_queue.record_app_blocked(name)

            # Thông báo cho Tray UI
            if self.on_block_attempt:
                try:
                    self.on_block_attempt(name)
                except Exception:
                    pass

            # Terminate (SIGTERM) - cho phép cleanup
            proc.terminate()
            try:
                proc.wait(timeout=APP_KILL_GRACE_PERIOD)
            except psutil.TimeoutExpired:
                # Nếu process không chịu thoát, kill cứng
                proc.kill()
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.error(f"Không thể kill {name}: {e}")
