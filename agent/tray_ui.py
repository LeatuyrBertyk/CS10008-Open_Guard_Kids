"""Tray UI - giao diện cho trẻ ở khay hệ thống.

Tuân thủ nguyên tắc NT1 (con phải biết phần mềm đang chạy):
- Luôn có biểu tượng ở khay đồng hồ
- Click chuột phải → menu
- Click menu → mở cửa sổ chi tiết

Cửa sổ chi tiết cho con thấy:
- Thời gian còn lại hôm nay
- Lý do bị chặn (nếu có)
- Nút "Xin thêm giờ"
- Nút "Con nghĩ trang này bị chặn nhầm"
- Thông tin minh bạch (bố mẹ đặt luật này, lúc nào)
"""

import threading
import time
import logging
import webbrowser
import requests
from pathlib import Path
from typing import Optional

from shared.constants import LOCAL_IPC_HOST, LOCAL_IPC_PORT, LOCAL_TOKEN_FILE
from agent.local_cache import LocalCache

logger = logging.getLogger("ogk.agent.tray")

# Cố gắng import pystray + PIL (cho icon)
try:
    import pystray
    from pystray import MenuItem as Item
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    logger.warning("pystray/Pillow chưa cài, Tray UI sẽ ở chế độ console")

# Cố gắng import tkinter (cho cửa sổ popup)
try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog
    HAS_TK = True
except ImportError:
    HAS_TK = False
    logger.warning("tkinter chưa có, sẽ không có cửa sổ popup")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = PROJECT_ROOT / LOCAL_TOKEN_FILE


# ==========================================
# Icon cho khay hệ thống
# ==========================================
def create_icon_image(color: str = "blue") -> "Image.Image":
    """Tạo ảnh icon đơn giản cho khay."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Vẽ hình khiên (đơn giản)
    color_map = {
        "blue": (44, 123, 229, 255),
        "green": (0, 185, 107, 255),
        "yellow": (245, 166, 35, 255),
        "red": (231, 76, 60, 255),
    }
    c = color_map.get(color, color_map["blue"])
    draw.ellipse([8, 8, 56, 56], fill=c)
    draw.text((20, 18), "OGK", fill="white")
    return img


# ==========================================
# Cửa sổ thông tin cho con
# ==========================================
class InfoWindow:
    """Cửa sổ hiển thị thông tin cho con."""

    def __init__(self, client, on_request_extra_time, on_report_false_block):
        """
        Args:
            client: HTTP client gọi local server
            on_request_extra_time: callback khi con bấm "Xin thêm giờ"
            on_report_false_block: callback khi con báo chặn nhầm
        """
        self.client = client
        self.on_request_extra_time = on_request_extra_time
        self.on_report_false_block = on_report_false_block
        self.root: Optional[tk.Tk] = None

    def show(self):
        """Hiển thị cửa sổ (tạo mới nếu chưa có)."""
        if not HAS_TK:
            print("[TRAY] tkinter không có, không thể hiện cửa sổ")
            return

        if self.root is not None:
            # Đã có cửa sổ, đưa lên trên
            self.root.lift()
            self.root.focus_force()
            self.refresh()
            return

        self.root = tk.Tk()
        self.root.title("OGK - Phụ huynh đang hỗ trợ bạn")
        self.root.geometry("500x500")
        self.root.resizable(False, False)

        # Cố gắng đặt icon
        try:
            self.root.iconphoto(False, tk.PhotoImage(data=self._icon_photo()))
        except Exception:
            pass

        # Header
        header = tk.Frame(self.root, bg="#2c7be5", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="🛡️ OGK Parental Control",
            font=("Arial", 18, "bold"), bg="#2c7be5", fg="white"
        ).pack(pady=10)
        tk.Label(
            header, text="Bố mẹ đang hỗ trợ bạn dùng máy an toàn",
            font=("Arial", 10), bg="#2c7be5", fg="white"
        ).pack()

        # Body
        body = tk.Frame(self.root, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        # Thời gian
        self.time_label = tk.Label(
            body, text="⏱️ Đang tải...", font=("Arial", 14)
        )
        self.time_label.pack(pady=10)

        # Trạng thái
        self.status_label = tk.Label(body, text="", font=("Arial", 11), fg="#666")
        self.status_label.pack(pady=5)

        # Policy info
        self.policy_text = tk.Text(body, height=8, font=("Consolas", 10), state="disabled")
        self.policy_text.pack(fill="x", pady=10)

        # Buttons
        btn_frame = tk.Frame(body)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="⏰ Xin thêm giờ", command=self._on_extra_time,
            bg="#f5a623", fg="white", font=("Arial", 11, "bold"),
            padx=20, pady=8, relief="flat"
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="🚫 Bị chặn nhầm?", command=self._on_false_block,
            bg="#2c7be5", fg="white", font=("Arial", 11, "bold"),
            padx=20, pady=8, relief="flat"
        ).pack(side="left", padx=5)

        # Footer
        tk.Label(
            body, text="(Bố mẹ sẽ nhận được thông báo và phản hồi sớm nhất)",
            font=("Arial", 9), fg="#888"
        ).pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh()
        self.root.mainloop()

    def _icon_photo(self) -> bytes:
        """Tạo ảnh PNG nhỏ làm icon cửa sổ."""
        import io
        img = create_icon_image("blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def refresh(self):
        """Làm mới thông tin từ local server."""
        if not self.root:
            return
        try:
            state = self.client.get_state()
            if "error" in state:
                self.time_label.config(text="⚠️ Không kết nối được service")
                return

            used = state.get("usage_minutes_today", 0)
            max_min = state.get("max_minutes_per_day", 0)
            remaining = max(0, max_min - used)
            is_locked = state.get("is_locked", False)
            policy = state.get("current_policy", {})

            # Màu sắc theo thời gian còn lại
            color = "#2c7be5"
            if remaining <= 0:
                color = "#e74c3c"
            elif remaining < 30:
                color = "#f5a623"
            elif remaining < 60:
                color = "#f5a623"

            self.time_label.config(
                text=f"⏱️ Còn lại hôm nay: {remaining} phút",
                fg=color,
            )
            self.status_label.config(
                text=f"Đã dùng: {used} / {max_min} phút"
                + ("  •  🔒 MÁY ĐÃ BỊ KHÓA" if is_locked else "")
            )

            # Policy info
            self.policy_text.config(state="normal")
            self.policy_text.delete("1.0", "end")
            info = f"""📋 Luật hiện tại (đặt bởi bố mẹ):
• Ứng dụng bị chặn: {', '.join(policy.get('blocked_apps', [])) or '(không)'}
• Website bị chặn: {', '.join(policy.get('blocked_domains', [])) or '(không)'}
• Giờ đi ngủ: {policy.get('bedtime_start', '?')} - {policy.get('bedtime_end', '?')}
• Tối đa/ngày: {policy.get('max_minutes_per_day', '?')} phút
"""
            self.policy_text.insert("1.0", info)
            self.policy_text.config(state="disabled")
        except Exception as e:
            logger.error(f"Lỗi refresh: {e}")

    def _on_extra_time(self):
        """Con bấm 'Xin thêm giờ'."""
        if HAS_TK:
            reason = simpledialog.askstring(
                "Xin thêm giờ",
                "Bạn cần thêm bao nhiêu phút và vì lý do gì?",
                parent=self.root,
            )
        else:
            reason = "Con xin thêm giờ"

        if not reason:
            return

        try:
            self.on_request_extra_time({"reason": reason, "extra_minutes": 30})
            if HAS_TK:
                messagebox.showinfo(
                    "Đã gửi",
                    "Đã gửi yêu cầu xin thêm giờ đến bố mẹ.\nVui lòng chờ phản hồi.",
                    parent=self.root,
                )
        except Exception as e:
            if HAS_TK:
                messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_false_block(self):
        """Con báo chặn nhầm."""
        if HAS_TK:
            reason = simpledialog.askstring(
                "Bị chặn nhầm",
                "Bạn nghĩ trang/app nào bị chặn nhầm?",
                parent=self.root,
            )
        else:
            reason = "Con nghĩ bị chặn nhầm"

        if not reason:
            return

        try:
            self.on_report_false_block({"reason": reason})
            if HAS_TK:
                messagebox.showinfo(
                    "Đã gửi",
                    "Đã gửi báo cáo đến bố mẹ.\nHọ sẽ xem xét và phản hồi.",
                    parent=self.root,
                )
        except Exception as e:
            if HAS_TK:
                messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_close(self):
        """Đóng cửa sổ (chỉ ẩn, không thoát chương trình)."""
        if self.root:
            self.root.destroy()
            self.root = None


# ==========================================
# HTTP client gọi local server
# ==========================================
class TrayClient:
    """Client gọi LocalServer (chạy trong service)."""

    def __init__(self):
        if TOKEN_PATH.exists():
            self.token = TOKEN_PATH.read_text().strip()
        else:
            self.token = ""
        self.base = f"http://{LOCAL_IPC_HOST}:{LOCAL_IPC_PORT}"

    def get_state(self) -> dict:
        """Lấy trạng thái hiện tại từ service."""
        try:
            r = requests.get(
                f"{self.base}/state",
                headers={"Authorization": "Bearer " + self.token},
                timeout=2,
            )
            return r.json() if r.status_code == 200 else {"error": "no_service"}
        except Exception as e:
            return {"error": str(e)}

    def send_request(self, request_type: str, body: dict) -> dict:
        """Gửi yêu cầu từ con (xin thêm giờ / bị chặn nhầm)."""
        path = "/request-extra-time" if request_type == "extra_time" else "/report-false-block"
        try:
            r = requests.post(
                f"{self.base}{path}",
                json=body,
                headers={"Authorization": "Bearer " + self.token},
                timeout=5,
            )
            return r.json() if r.status_code == 200 else {"error": "failed"}
        except Exception as e:
            return {"error": str(e)}


# ==========================================
# Tray icon (pystray)
# ==========================================
class TrayApp:
    """Ứng dụng khay hệ thống."""

    def __init__(self, on_request_extra_time, on_report_false_block):
        self.tray_client = TrayClient()
        self.info_window = InfoWindow(
            self.tray_client,
            on_request_extra_time,
            on_report_false_block,
        )
        self.icon: Optional[pystray.Icon] = None

    def start(self):
        """Khởi động tray icon."""
        if not HAS_PYSTRAY:
            logger.warning("Không có pystray, chạy ở chế độ console")
            return

        menu = pystray.Menu(
            Item("📊 Mở bảng thông tin", self._show_info, default=True),
            Item("⏰ Xin thêm giờ", self._request_time),
            Item("🚫 Bị chặn nhầm?", self._report_block),
            pystray.Menu.SEPARATOR,
            Item("❌ Thoát", self._quit),
        )

        self.icon = pystray.Icon(
            "ogk_agent",
            create_icon_image("blue"),
            "OGK Parental Control (đang chạy)",
            menu,
        )
        self.icon.run_detached()
        logger.info("Tray icon started")

    def stop(self):
        """Dừng tray icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def notify(self, title: str, message: str):
        """Hiển thị thông báo (balloon notification)."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def _show_info(self, icon, item):
        """Mở cửa sổ thông tin."""
        threading.Thread(target=self.info_window.show, daemon=True).start()

    def _request_time(self, icon, item):
        """Menu item: Xin thêm giờ."""
        self.info_window._on_extra_time()

    def _report_block(self, icon, item):
        """Menu item: Bị chặn nhầm."""
        self.info_window._on_false_block()

    def _quit(self, icon, item):
        """Menu item: Thoát."""
        self.stop()
