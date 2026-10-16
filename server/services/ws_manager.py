"""WebSocket Connection Manager.

Quản lý các kết nối WebSocket từ Agent, cho phép server
đẩy lệnh realtime (lock_now, policy_update, ...) xuống agent
mà không cần đợi heartbeat tiếp theo.

Sử dụng:
    from server.services.ws_manager import ws_manager
    await ws_manager.send_to_device(device_id, {"action": "lock_now"})
"""

from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """Quản lý các WebSocket connection theo device_id.

    Mỗi device có thể có nhiều kết nối (vd cả Agent service và Tray UI)
    - service dùng để nhận policy_update
    - tray UI dùng để nhận thông báo cho con
    """

    def __init__(self):
        # Map: device_id -> set of WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, device_id: int):
        """Đăng ký một connection mới."""
        await websocket.accept()
        async with self._lock:
            if device_id not in self._connections:
                self._connections[device_id] = set()
            self._connections[device_id].add(websocket)
        print(f"[WS] Device {device_id} connected. Active: {self.active_count()}")

    def disconnect(self, websocket: WebSocket, device_id: int):
        """Hủy đăng ký một connection."""
        if device_id in self._connections:
            self._connections[device_id].discard(websocket)
            if not self._connections[device_id]:
                del self._connections[device_id]
        print(f"[WS] Device {device_id} disconnected. Active: {self.active_count()}")

    async def send_to_device(self, device_id: int, message: dict) -> int:
        """Gửi message tới tất cả connections của 1 device.

        Returns:
            Số connection đã gửi thành công
        """
        if device_id not in self._connections:
            return 0

        connections = self._connections[device_id].copy()
        sent = 0
        for ws in connections:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception as e:
                print(f"[WS] Gửi lỗi tới device {device_id}: {e}")
                # Tự động dọn connection lỗi
                self.disconnect(ws, device_id)
        return sent

    async def broadcast(self, message: dict) -> int:
        """Gửi tới tất cả devices đang kết nối.

        Returns:
            Tổng số connection đã gửi
        """
        total = 0
        for device_id in list(self._connections.keys()):
            total += await self.send_to_device(device_id, message)
        return total

    def is_online(self, device_id: int) -> bool:
        """Kiểm tra device có đang kết nối WS không."""
        return device_id in self._connections and len(self._connections[device_id]) > 0

    def online_devices(self) -> list[int]:
        """Danh sách device_id đang online (có WS)."""
        return [d for d, conns in self._connections.items() if conns]

    def active_count(self) -> int:
        """Tổng số connection đang active."""
        return sum(len(conns) for conns in self._connections.values())


# Singleton toàn cục
ws_manager = ConnectionManager()


# ==========================================
# Helper: gửi lệnh phổ biến
# ==========================================
async def send_lock_now(device_id: int, reason: str = "Phụ huynh yêu cầu"):
    """Lệnh: khóa máy ngay lập tức."""
    return await ws_manager.send_to_device(device_id, {
        "type": "command",
        "action": "lock_now",
        "reason": reason,
    })


async def send_unlock(device_id: int):
    """Lệnh: mở khóa máy ngay."""
    return await ws_manager.send_to_device(device_id, {
        "type": "command",
        "action": "unlock",
    })


async def send_policy_update(device_id: int, policy: dict):
    """Lệnh: cập nhật policy ngay lập tức (không đợi heartbeat 60s)."""
    return await ws_manager.send_to_device(device_id, {
        "type": "command",
        "action": "policy_update",
        "policy": policy,
    })


async def send_notify(device_id: int, title: str, message: str):
    """Lệnh: hiển thị thông báo (NT1) cho con."""
    return await ws_manager.send_to_device(device_id, {
        "type": "notify",
        "title": title,
        "message": message,
    })
