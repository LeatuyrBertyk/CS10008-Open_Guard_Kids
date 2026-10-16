"""Module đăng ký máy (enrollment) - chạy lần đầu tiên.

Luồng:
1. Người dùng chạy: python -m agent.enroll --code DEMO2024
2. Script gọi ServerClient.enroll(code)
3. Lưu device_token vào config
4. In hướng dẫn tiếp theo
"""

import sys
import argparse
from pathlib import Path

# Thêm project root vào path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.config import is_enrolled, get
from agent.client import ServerClient


def run_enrollment(code: str):
    """Thực hiện đăng ký máy với mã enroll_code."""
    print()
    print("=" * 60)
    print("OGK AGENT - ĐĂNG KÝ MÁY")
    print("=" * 60)

    if is_enrolled():
        print(f"⚠️  Máy này đã được đăng ký trước đó (device_id={get('device_id')}).")
        ans = input("Bạn có muốn đăng ký lại? (y/N): ").strip().lower()
        if ans != "y":
            print("Hủy.")
            return

    print(f"📡 Server: {get('server_url')}")
    print(f"🔑 Mã đăng ký: {code}")
    print()

    client = ServerClient()
    print("⏳ Đang liên hệ server...")
    if not client.ping():
        print(f"❌ Không kết nối được tới server tại {client.base_url}")
        print("   Vui lòng kiểm tra:")
        print("   - Server đã chạy chưa?")
        print("   - URL trong config.json đúng chưa?")
        return

    try:
        data = client.enroll(code)
    except Exception as e:
        print(f"❌ Đăng ký thất bại: {e}")
        return

    print()
    print("✅ ĐĂNG KÝ THÀNH CÔNG!")
    print("-" * 60)
    print(f"  Device ID : {data['device_id']}")
    print(f"  Child     : {data['child_name']}")
    print(f"  Token     : {data['device_token'][:16]}...")
    print()
    print("📋 Luật ban đầu:")
    policy = data.get("policy", {})
    print(f"  - Tối đa: {policy.get('max_minutes_per_day')} phút/ngày")
    print(f"  - App chặn: {policy.get('blocked_apps', [])}")
    print(f"  - Web chặn: {policy.get('blocked_domains', [])}")
    print()
    print("🚀 Bước tiếp theo: chạy Agent")
    print("   python -m agent.main --dev       (chế độ dev)")
    print("   python -m agent.main             (chế độ service)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Đăng ký máy với OGK Server")
    parser.add_argument(
        "--code", "-c",
        required=True,
        help="Mã đăng ký do phụ huynh cấp (ví dụ: DEMO2024)",
    )
    args = parser.parse_args()
    run_enrollment(args.code)


if __name__ == "__main__":
    main()
