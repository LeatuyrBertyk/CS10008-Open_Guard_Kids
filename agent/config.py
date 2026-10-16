"""Cấu hình cho Agent (phần mềm chạy trên máy con).

Đọc thông tin từ file config.json: server URL, device token, ...
"""

import json
import os
from pathlib import Path
from typing import Optional

from shared.constants import (
    AGENT_CONFIG_FILE,
    DEFAULT_SERVER_URL,
    HEARTBEAT_INTERVAL_SECONDS,
)


# Thư mục gốc project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / AGENT_CONFIG_FILE


# ==========================================
# Cấu hình mặc định
# ==========================================
DEFAULT_CONFIG = {
    "server_url": DEFAULT_SERVER_URL,
    "device_token": None,  # sẽ được set sau khi enroll
    "enrollment_code": None,  # mã enroll dùng 1 lần
    "device_id": None,  # ID thiết bị sau khi enroll
    "hostname": os.environ.get("COMPUTERNAME", "unknown"),
    "heartbeat_interval": HEARTBEAT_INTERVAL_SECONDS,
}


def load_config() -> dict:
    """Đọc config từ file. Nếu chưa có file thì tạo mới với giá trị mặc định."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Merge với default để đảm bảo có đủ key
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        return merged
    except Exception as e:
        print(f"[CONFIG] Lỗi đọc config: {e}, dùng mặc định")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Lưu config ra file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_config(updates: dict) -> dict:
    """Cập nhật một số trường trong config."""
    config = load_config()
    config.update(updates)
    save_config(config)
    return config


def get(key: str, default=None):
    """Lấy 1 giá trị config (tiện hơn load_config()['key'])."""
    return load_config().get(key, default)


def is_enrolled() -> bool:
    """Đã enroll chưa? (có device_token chưa)."""
    return bool(get("device_token"))
