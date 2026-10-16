"""Module DNS Proxy - lọc domain theo policy.

Cách hoạt động:
- Lắng nghe UDP cổng 53 (DNS) trên 127.0.0.1
- Khi có truy vấn DNS, parse lấy domain
- Nếu domain trong blocked_domains → trả về 0.0.0.0
- Nếu domain trong allowlist → chuyển tiếp tới DNS thật
- Nếu không chặn → chuyển tiếp tới DNS upstream (8.8.8.8)

LƯU Ý: Chỉ hoạt động khi Windows được cấu hình dùng 127.0.0.1 làm DNS.
Cấu hình bằng: netsh interface ip set dns "Wi-Fi" static 127.0.0.1
"""

import threading
import socket
import logging
from typing import Optional, Callable, List

try:
    from dnslib import DNSRecord, RR, A, QTYPE
    from dnslib.server import DNSServer, BaseResolver
except ImportError:
    DNSRecord = None
    BaseResolver = None
    DNSServer = None

from shared.constants import (
    DNS_PROXY_PORT,
    DNS_UPSTREAM_HOST,
    DNS_UPSTREAM_PORT,
)
from shared.allowlist import is_domain_allowed
from agent.events import EventQueue

logger = logging.getLogger("ogk.agent.dns_proxy")


class FilteringResolver(BaseResolver if BaseResolver else object):
    """DNS resolver có lọc domain theo policy."""

    def __init__(
        self,
        event_queue: EventQueue,
        upstream_host: str = DNS_UPSTREAM_HOST,
        upstream_port: int = DNS_UPSTREAM_PORT,
        on_block: Optional[Callable[[str], None]] = None,
    ):
        if BaseResolver:
            super().__init__()
        self.event_queue = event_queue
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.on_block = on_block
        self._blocked_domains: List[str] = []
        self._allowed_domains_extra: List[str] = []
        self._is_locked = False

        # Cache các truy vấn upstream để tránh gọi lại
        self._upstream_cache = {}

    def update_policy(self, blocked_domains: List[str], allowed_domains: List[str] = None):
        """Cập nhật domain chặn/cho phép từ policy."""
        self._blocked_domains = [d.lower().strip() for d in (blocked_domains or []) if d]
        self._allowed_domains_extra = [d.lower().strip() for d in (allowed_domains or []) if d]
        self._upstream_cache.clear()
        logger.info(f"Blocked domains: {self._blocked_domains}, Allowed: {self._allowed_domains_extra}")

    def set_locked(self, locked: bool):
        """Khi khóa máy, chặt hơn nữa (chỉ allowlist hoạt động)."""
        self._is_locked = locked

    def _is_blocked(self, domain: str) -> bool:
        """Kiểm tra domain có bị chặn không."""
        domain = domain.lower().strip().rstrip(".")
        if not domain:
            return False

        # Bỏ www. phía trước
        if domain.startswith("www."):
            domain_check = domain[4:]
        else:
            domain_check = domain

        # 1. Kiểm tra allowlist mặc định (111, gov.vn, ...)
        if is_domain_allowed(domain):
            return False

        # 2. Kiểm tra allowlist thêm từ policy
        if domain_check in self._allowed_domains_extra:
            return False

        # 3. Nếu đang lock máy, chặn mọi thứ không trong allowlist
        if self._is_locked:
            return True

        # 4. Kiểm tra blocked list
        for blocked in self._blocked_domains:
            if domain_check == blocked or domain_check.endswith("." + blocked):
                return True

        return False

    def resolve(self, request, handler):
        """Xử lý 1 truy vấn DNS.

        Được gọi bởi DNSServer cho mỗi query.
        """
        if not DNSRecord:
            return request

        reply = request.reply()
        qname = str(request.q.qname).rstrip(".")

        # Tìm câu trả lời
        if self._is_blocked(qname):
            logger.info(f"BLOCKED: {qname}")
            # Trả về 0.0.0.0 để trình duyệt báo "không truy cập được"
            reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
            self.event_queue.record_web_blocked(qname)
            if self.on_block:
                try:
                    self.on_block(qname)
                except Exception:
                    pass
        else:
            # Chuyển tiếp tới DNS upstream
            upstream_reply = self._query_upstream(request)
            if upstream_reply:
                return upstream_reply
            # Nếu upstream lỗi, trả về empty reply
        return reply

    def _query_upstream(self, request):
        """Hỏi DNS upstream (8.8.8.8) và trả về kết quả."""
        try:
            data = request.pack()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            sock.sendto(data, (self.upstream_host, self.upstream_port))
            response_data, _ = sock.recvfrom(4096)
            sock.close()
            return DNSRecord.parse(response_data)
        except Exception as e:
            logger.warning(f"Upstream DNS query thất bại: {e}")
            return None


class DNSProxy:
    """DNS proxy server - khởi động và dừng dễ dàng."""

    def __init__(
        self,
        event_queue: EventQueue,
        on_block: Optional[Callable[[str], None]] = None,
    ):
        if not DNSRecord or not DNSServer:
            raise ImportError(
                "Cần cài thư viện 'dnslib' để chạy DNS proxy: pip install dnslib"
            )
        self.resolver = FilteringResolver(event_queue, on_block=on_block)
        self.server: Optional[DNSServer] = None
        self._thread: Optional[threading.Thread] = None
        logger.info("DNSProxy initialized")

    def update_policy(self, blocked_domains: List[str], allowed_domains: List[str] = None):
        self.resolver.update_policy(blocked_domains, allowed_domains)

    def set_locked(self, locked: bool):
        self.resolver.set_locked(locked)

    def start(self, port: int = DNS_PROXY_PORT):
        """Khởi động DNS server trên cổng 53 (mặc định)."""
        if self.server:
            return
        try:
            self.server = DNSServer(self.resolver, port=port, address="127.0.0.1")
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()
            logger.info(f"DNS proxy started on 127.0.0.1:{port}")
        except PermissionError:
            logger.error(
                f"Không có quyền bind cổng {port}. "
                "Cần chạy với quyền Administrator, hoặc thay đổi port."
            )
            self.server = None
        except OSError as e:
            logger.error(f"Không start được DNS server: {e}")
            self.server = None

    def stop(self):
        """Dừng DNS server."""
        if self.server:
            try:
                self.server.stop()
            except Exception:
                pass
            self.server = None
            logger.info("DNS proxy stopped")
