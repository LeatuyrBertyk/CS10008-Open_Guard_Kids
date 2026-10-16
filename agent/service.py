"""Windows Service cho OGK Agent.

Đăng ký service:
    python -m agent.service install
    python -m agent.service start

Service chạy nền, có quyền cao (LocalSystem), chịu trách nhiệm:
- Heartbeat mỗi 60s
- Chặn ứng dụng
- DNS proxy
- Screen time counter
- Lưu event vào local cache

Tray UI là process RIÊNG, chạy dưới quyền user.
Hai bên giao tiếp qua LocalServer.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Đảm bảo project root trong sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================
# Class quản lý Agent (dùng chung cho service & dev mode)
# ==========================================
class AgentCore:
    """Lõi của Agent - quản lý tất cả module con."""

    def __init__(self):
        from agent.config import load_config
        from agent.client import ServerClient
        from agent.local_cache import LocalCache
        from agent.events import EventQueue
        from agent.heartbeat import HeartbeatThread
        from agent.screentime import ScreenTimeCounter
        from agent.app_controller import AppController
        from agent.local_server import LocalServer

        self.logger = logging.getLogger("ogk.agent.core")

        # Load config
        self.config = load_config()

        # Khởi tạo các thành phần
        self.client = ServerClient()
        self.cache = LocalCache()
        self.events = EventQueue(self.cache, self.client)
        self.heartbeat = HeartbeatThread(
            self.client,
            self.cache,
            on_policy_update=self._on_policy_update,
            on_force_lock=self._on_force_lock,
        )
        self.screentime = ScreenTimeCounter(
            self.cache,
            on_limit_exceeded=self._on_lock_exceeded,
        )
        self.app_controller = AppController(
            self.events,
            on_block_attempt=self._on_app_blocked,
        )

        # DNS proxy - optional (cần dnslib)
        self.dns_proxy = None
        try:
            from agent.dns_proxy import DNSProxy
            self.dns_proxy = DNSProxy(
                self.events,
                on_block=self._on_web_blocked,
            )
        except ImportError:
            self.logger.warning("DNS proxy không khả dụng (thiếu dnslib)")

        # Local server (cho Tray UI)
        self.local_server = LocalServer(
            self.cache,
            get_status_func=self._get_status,
            on_request_extra_time=self._handle_extra_time_request,
            on_report_false_block=self._handle_false_block_report,
        )

        # Apply policy đã lưu trong cache (nếu có)
        saved_policy = self.cache.get_state("current_policy", {})
        if saved_policy:
            self._apply_policy(saved_policy)

    # ==========================================
    # Lifecycle
    # ==========================================
    def start(self):
        """Khởi động tất cả module."""
        self.logger.info("Agent starting...")
        self.events.start()
        self.heartbeat.start()
        self.screentime.start()
        self.app_controller.start()
        if self.dns_proxy:
            try:
                self.dns_proxy.start()
            except Exception as e:
                self.logger.warning(f"DNS proxy không khởi động được: {e}")
        self.local_server.start()
        self.logger.info("Agent started")

    def stop(self):
        """Dừng tất cả module (gọi trước khi thoát)."""
        self.logger.info("Agent stopping...")
        try:
            self.events.flush_now()
        except Exception:
            pass
        self.events.stop()
        self.heartbeat.stop()
        self.screentime.stop()
        self.app_controller.stop()
        if self.dns_proxy:
            self.dns_proxy.stop()
        self.local_server.stop()
        self.logger.info("Agent stopped")

    # ==========================================
    # Callback
    # ==========================================
    def _on_policy_update(self, policy: dict):
        """Khi nhận policy mới từ server."""
        self._apply_policy(policy)

    def _on_force_lock(self):
        """Server yêu cầu khóa máy ngay."""
        self.logger.warning("Server yêu cầu khóa máy")
        self.cache.set_state("is_locked", True)
        self.app_controller.set_locked(True)
        if self.dns_proxy:
            self.dns_proxy.set_locked(True)

    def _on_lock_exceeded(self):
        """Vượt giới hạn thời gian → tự khóa."""
        self.logger.warning("Vượt giới hạn thời gian - tự khóa máy")
        self.cache.set_state("is_locked", True)
        self.app_controller.set_locked(True)
        if self.dns_proxy:
            self.dns_proxy.set_locked(True)

    def _on_app_blocked(self, app_name: str):
        """App bị chặn."""
        self.logger.info(f"App blocked: {app_name}")

    def _on_web_blocked(self, domain: str):
        """Web bị chặn."""
        self.logger.info(f"Web blocked: {domain}")

    def _apply_policy(self, policy: dict):
        """Áp dụng policy vào các module."""
        if not policy:
            return
        self.logger.info(f"Applying policy: max={policy.get('max_minutes_per_day')}min")
        if "max_minutes_per_day" in policy:
            self.screentime.set_limit(policy["max_minutes_per_day"])
        if "blocked_apps" in policy:
            self.app_controller.update_policy(policy["blocked_apps"])
        if self.dns_proxy and "blocked_domains" in policy:
            self.dns_proxy.update_policy(
                policy.get("blocked_domains", []),
                policy.get("allowed_domains", []),
            )

    def _get_status(self) -> dict:
        """Trả về trạng thái hiện tại cho Tray UI."""
        return {
            "current_policy": self.cache.get_state("current_policy", {}),
            "max_minutes_per_day": self.cache.get_state("current_policy", {}).get("max_minutes_per_day", 0),
            "is_locked": self.cache.get_state("is_locked", False),
        }

    def _handle_extra_time_request(self, body: dict):
        """Con gửi yêu cầu xin thêm giờ."""
        try:
            result = self.client.create_request(
                request_type="extra_time",
                reason=body.get("reason", "Con xin thêm giờ"),
                extra_minutes=body.get("extra_minutes", 15),
            )
            self.logger.info(f"Yêu cầu xin thêm giờ đã gửi: id={result.get('id')}")
        except Exception as e:
            self.logger.error(f"Không gửi được yêu cầu: {e}")

    def _handle_false_block_report(self, body: dict):
        """Con báo chặn nhầm."""
        try:
            self.client.create_request(
                request_type="report_false_block",
                reason=body.get("reason", "Bị chặn nhầm"),
                context=body,
            )
            self.logger.info("Báo cáo chặn nhầm đã gửi")
        except Exception as e:
            self.logger.error(f"Không gửi được báo cáo: {e}")


# ==========================================
# Windows Service wrapper (pywin32)
# ==========================================
def run_as_service():
    """Chạy Agent như một Windows Service."""
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
    except ImportError:
        print("pywin32 chưa cài. Chạy: pip install pywin32")
        sys.exit(1)

    class OGKAgentService(win32serviceutil.ServiceFramework):
        """Windows Service thực sự."""

        _svc_name_ = "OGKAgent"
        _svc_display_name_ = "OGK Parental Control Agent"
        _svc_description_ = "Giám sát và quản lý việc sử dụng máy tính của trẻ em"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, 0)
            self.core: Optional[AgentCore] = None

        def SvcStop(self):
            """Được gọi khi service được yêu cầu dừng."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.core:
                self.core.stop()

        def SvcDoRun(self):
            """Được gọi khi service bắt đầu chạy."""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            try:
                self.core = AgentCore()
                self.core.start()
                # Chờ tín hiệu dừng
                win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            except Exception as e:
                servicemanager.LogErrorMsg(str(e))
            finally:
                if self.core:
                    self.core.stop()

    if len(sys.argv) == 1:
        # Chạy từ Service Control Manager
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(OGKAgentService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception as e:
            print(f"Lỗi service: {e}")
            sys.exit(1)
    else:
        # Chạy từ command line: install, start, stop, remove
        win32serviceutil.HandleCommandLine(OGKAgentService)


if __name__ == "__main__":
    run_as_service()
