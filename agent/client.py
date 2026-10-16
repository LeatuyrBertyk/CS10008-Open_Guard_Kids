"""HTTP client giao tiếp với Server.

Cung cấp class ServerClient với các method:
- enroll(): đăng ký máy mới
- heartbeat(): gửi heartbeat
- push_events(): đẩy sự kiện
- create_request(): tạo yêu cầu

Có xử lý timeout, retry, lỗi mạng.
"""

import time
import socket
import platform
import logging
from typing import Optional
from uuid import uuid4

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.constants import (
    HEARTBEAT_RETRY_TIMES,
    REQUEST_TIMEOUT_SECONDS,
)
from agent.config import get


logger = logging.getLogger("ogk.agent.client")


class ServerClient:
    """Client gọi API lên Server."""

    def __init__(self, base_url: Optional[str] = None, device_token: Optional[str] = None):
        """Khởi tạo client.

        Args:
            base_url: URL của server, mặc định đọc từ config
            device_token: token xác thực device, mặc định đọc từ config
        """
        self.base_url = (base_url or get("server_url", "http://127.0.0.1:8000")).rstrip("/")
        self.device_token = device_token or get("device_token")

        # Tạo session với retry tự động
        self.session = requests.Session()
        retry_strategy = Retry(
            total=HEARTBEAT_RETRY_TIMES,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ==========================================
    # Helpers
    # ==========================================
    def _headers(self) -> dict:
        """Headers chung cho mọi request."""
        headers = {"Content-Type": "application/json"}
        if self.device_token:
            headers["Authorization"] = f"Bearer {self.device_token}"
        return headers

    def _url(self, path: str) -> str:
        """Ghép URL đầy đủ."""
        return f"{self.base_url}{path}"

    def _get_local_info(self) -> dict:
        """Lấy thông tin máy local để enroll."""
        hostname = socket.gethostname()
        os_ver = f"Windows {platform.release()} {platform.version()}"
        mac = self._get_mac_address()
        return {"hostname": hostname, "os_version": os_ver, "mac_address": mac}

    @staticmethod
    def _get_mac_address() -> str:
        """Lấy địa chỉ MAC (best-effort)."""
        try:
            mac = uuid4().hex  # fallback
            for iface in platform.processor():  # dummy
                pass
            # Lấy MAC thật
            import uuid as _uuid
            mac = f"{(int.from_bytes(_uuid.getnode().to_bytes(6, 'little'), 'little')):012x}"
            return ":".join(mac[i:i+2] for i in range(0, 12, 2))
        except Exception:
            return "00:00:00:00:00:00"

    # ==========================================
    # Public API
    # ==========================================
    def enroll(self, enrollment_code: str) -> dict:
        """Đăng ký máy mới với server.

        Args:
            enrollment_code: mã enroll do phụ huynh cấp

        Returns:
            Dict với device_id, device_token, policy ban đầu

        Raises:
            Exception nếu enroll thất bại
        """
        info = self._get_local_info()
        payload = {
            "device_code": enrollment_code,
            **info,
        }
        resp = self.session.post(
            self._url("/api/devices/enroll"),
            json=payload,
            headers=self._headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise Exception(f"Enroll thất bại ({resp.status_code}): {detail}")

        data = resp.json()
        # Cập nhật token vào config
        from agent.config import update_config
        update_config({
            "device_token": data["device_token"],
            "device_id": data["device_id"],
        })
        self.device_token = data["device_token"]
        return data

    def heartbeat(
        self,
        usage_minutes_today: int,
        is_locked: bool = False,
        pending_events_count: int = 0,
    ) -> dict:
        """Gửi heartbeat lên server.

        Returns:
            Dict với ack, server_time, policy, force_lock
        """
        if not self.device_token:
            raise Exception("Chưa enroll, không thể gửi heartbeat")

        payload = {
            "usage_minutes_today": usage_minutes_today,
            "is_locked": is_locked,
            "pending_events_count": pending_events_count,
        }
        resp = self.session.post(
            self._url("/api/devices/heartbeat"),
            json=payload,
            headers=self._headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()

    def push_events(self, events: list) -> dict:
        """Đẩy danh sách sự kiện lên server.

        Args:
            events: list các dict event (đã có timestamp)

        Returns:
            Dict với số sự kiện accepted/rejected
        """
        if not self.device_token:
            raise Exception("Chưa enroll, không thể gửi events")
        if not events:
            return {"accepted": 0, "rejected": 0}

        payload = {"events": events}
        resp = self.session.post(
            self._url("/api/events"),
            json=payload,
            headers=self._headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()

    def create_request(
        self,
        request_type: str,
        reason: str,
        extra_minutes: int = 15,
        context: Optional[dict] = None,
    ) -> dict:
        """Con tạo yêu cầu gửi lên server."""
        if not self.device_token:
            raise Exception("Chưa enroll, không thể gửi yêu cầu")

        payload = {
            "request_type": request_type,
            "reason": reason,
            "extra_minutes": extra_minutes,
            "context": context,
        }
        resp = self.session.post(
            self._url("/api/requests"),
            json=payload,
            headers=self._headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()

    def ping(self) -> bool:
        """Kiểm tra server có sống không. Trả về True nếu OK."""
        try:
            resp = self.session.get(
                self._url("/api/health"),
                timeout=3,
            )
            return resp.status_code == 200
        except Exception:
            return False
