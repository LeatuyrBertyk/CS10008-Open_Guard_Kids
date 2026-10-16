"""Entry point chính của Agent.

Các chế độ chạy:
    python -m agent.main --dev          # chế độ development (foreground)
    python -m agent.main --tray         # chỉ chạy Tray UI
    python -m agent.main                # chế độ service (cần cài service trước)

Trong chế độ --dev: tất cả thread chạy trong 1 process, log ra console.
Trong chế độ --tray: chỉ chạy Tray UI, service phải chạy riêng.
Trong chế độ service: do Windows Service Manager quản lý.
"""

import sys
import signal
import time
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def setup_logging():
    """Cấu hình logging ra console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Tắt log quá ồn từ thư viện
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def run_dev_mode():
    """Chạy tất cả trong 1 process (foreground) - dùng để test."""
    from agent.service import AgentCore

    print("=" * 60)
    print("OGK Agent - DEV MODE")
    print("=" * 60)
    print("Nhấn Ctrl+C để dừng.")
    print()

    core = AgentCore()
    core.start()

    # Xử lý Ctrl+C
    def signal_handler(sig, frame):
        print("\nĐang dừng Agent...")
        core.stop()
        print("Đã dừng. Tạm biệt!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Vòng lặp vô hạn
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


def run_tray_only():
    """Chỉ chạy Tray UI (giả định service đã chạy riêng)."""
    from agent.tray_ui import TrayApp, HAS_TK, HAS_PYSTRAY
    from agent.client import ServerClient
    from agent.config import is_enrolled

    print("=" * 60)
    print("OGK Agent - TRAY UI ONLY")
    print("=" * 60)

    if not is_enrolled():
        print("⚠️  Chưa enroll! Chạy: python -m agent.enroll --code DEMO2024")
        return

    client = ServerClient()

    def on_extra_time(body):
        client.create_request(
            request_type="extra_time",
            reason=body.get("reason", ""),
            extra_minutes=body.get("extra_minutes", 15),
        )

    def on_false_block(body):
        client.create_request(
            request_type="report_false_block",
            reason=body.get("reason", ""),
            context=body,
        )

    app = TrayApp(on_extra_time, on_false_block)

    if HAS_TK:
        # Mở cửa sổ thông tin
        app.info_window.show()
    elif HAS_PYSTRAY:
        # Chỉ chạy tray icon
        app.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            app.stop()
    else:
        print("Không có pystray/tkinter, không thể hiển thị UI.")
        print("Vui lòng cài: pip install pystray pillow")


def main():
    parser = argparse.ArgumentParser(description="OGK Agent - chạy trên máy con")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Chạy ở chế độ dev (foreground, tất cả trong 1 process)",
    )
    parser.add_argument(
        "--tray",
        action="store_true",
        help="Chỉ chạy Tray UI",
    )
    args = parser.parse_args()

    setup_logging()

    # Kiểm tra enroll
    from agent.config import is_enrolled
    if not is_enrolled() and not args.tray:
        print("⚠️  Máy chưa được đăng ký với server.")
        print("Chạy: python -m agent.enroll --code DEMO2024")
        return

    if args.tray:
        run_tray_only()
    elif args.dev:
        run_dev_mode()
    else:
        # Mặc định = service mode
        from agent.service import run_as_service
        run_as_service()


if __name__ == "__main__":
    main()
