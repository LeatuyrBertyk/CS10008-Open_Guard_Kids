"""Local HTTP server - cho phép Tray UI giao tiếp với Service.

Service chạy dưới quyền SYSTEM, Tray UI chạy dưới quyền user.
Hai process này cần nói chuyện với nhau (Tray UI hỏi "còn bao nhiêu
phút?", Service trả lời).

Cách làm: Service mở 1 HTTP server trên 127.0.0.1:9999, Tray UI
gọi tới. Có token xác thực để chặn process khác gọi.
"""

import secrets
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse, parse_qs
import json

from shared.constants import LOCAL_IPC_HOST, LOCAL_IPC_PORT, LOCAL_TOKEN_FILE
from agent.local_cache import LocalCache

logger = logging.getLogger("ogk.agent.local_server")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = PROJECT_ROOT / LOCAL_TOKEN_FILE


def ensure_token() -> str:
    """Đảm bảo có token cục bộ, tạo mới nếu chưa có.

    Returns:
        Token string
    """
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    token = secrets.token_urlsafe(32)
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token)
    logger.info(f"Created new local token at {TOKEN_PATH}")
    return token


class LocalStateProvider:
    """Cung cấp trạng thái hiện tại cho Tray UI.

    Service khởi tạo class này và truyền vào handler.
    """

    def __init__(self, cache: LocalCache, get_status_func: Callable[[], dict]):
        self.cache = cache
        self.get_status = get_status_func

    def get_full_state(self) -> dict:
        """Trả về toàn bộ state để Tray UI hiển thị."""
        state = self.get_status()
        state["usage_minutes_today"] = self.cache.get_usage_today()
        state["is_locked"] = self.cache.get_state("is_locked", False)
        state["pending_events"] = self.cache.count_pending()
        return state


def make_handler(state_provider: LocalStateProvider, expected_token: str):
    """Tạo HTTP handler class với closure để capture state_provider và token."""

    class Handler(BaseHTTPRequestHandler):
        """HTTP request handler cho local IPC."""

        def log_message(self, format, *args):
            # Tắt log mặc định (gây noise)
            pass

        def _check_auth(self) -> bool:
            """Kiểm tra Authorization header có token đúng không."""
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return False
            return auth[7:] == expected_token

        def _send_json(self, code: int, data: dict):
            """Gửi response dạng JSON."""
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            """Xử lý GET request."""
            if not self._check_auth():
                self._send_json(401, {"error": "unauthorized"})
                return

            path = urlparse(self.path).path
            if path == "/state":
                self._send_json(200, state_provider.get_full_state())
            elif path == "/ping":
                self._send_json(200, {"pong": True})
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self):
            """Xử lý POST request (gửi yêu cầu từ con)."""
            if not self._check_auth():
                self._send_json(401, {"error": "unauthorized"})
                return

            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception:
                body = {}

            if path == "/request-extra-time":
                # Tray UI gửi yêu cầu xin thêm giờ
                self._send_json(200, {
                    "status": "queued",
                    "message": "Yêu cầu đang được gửi tới phụ huynh",
                })
                # Thực sự gọi server ở nơi khác (qua callback)
                if hasattr(state_provider, "on_request_extra_time"):
                    try:
                        state_provider.on_request_extra_time(body)
                    except Exception as e:
                        logger.error(f"Lỗi gửi yêu cầu: {e}")

            elif path == "/report-false-block":
                self._send_json(200, {"status": "queued"})
                if hasattr(state_provider, "on_report_false_block"):
                    try:
                        state_provider.on_report_false_block(body)
                    except Exception as e:
                        logger.error(f"Lỗi báo cáo: {e}")
            else:
                self._send_json(404, {"error": "not found"})

        def do_OPTIONS(self):
            """CORS preflight."""
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()

    return Handler


class LocalServer:
    """HTTP server chạy trong thread riêng, dùng cho IPC."""

    def __init__(
        self,
        cache: LocalCache,
        get_status_func: Callable[[], dict],
        on_request_extra_time: Optional[Callable[[dict], None]] = None,
        on_report_false_block: Optional[Callable[[dict], None]] = None,
    ):
        self.token = ensure_token()
        self.provider = LocalStateProvider(cache, get_status_func)
        if on_request_extra_time:
            self.provider.on_request_extra_time = on_request_extra_time
        if on_report_false_block:
            self.provider.on_report_false_block = on_report_false_block

        handler = make_handler(self.provider, self.token)
        self.httpd = HTTPServer((LOCAL_IPC_HOST, LOCAL_IPC_PORT), handler)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        logger.info(f"LocalServer will listen on {LOCAL_IPC_HOST}:{LOCAL_IPC_PORT}")

    def start(self):
        """Khởi động server trong thread nền."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("LocalServer started")

    def _serve(self):
        """Vòng lặp serve."""
        try:
            self.httpd.serve_forever()
        except Exception as e:
            logger.error(f"LocalServer crashed: {e}")
        finally:
            self._running = False

    def stop(self):
        """Dừng server."""
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        logger.info("LocalServer stopped")
