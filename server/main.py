"""OGK Server - FastAPI application chính.

Khởi động:
    uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

Hoặc:
    python -m server.main

Tính năng đã tích hợp (theo yêu cầu 2.2):
- TLS 1.2+ (qua uvicorn ssl options)
- WebSocket endpoint /ws/agent cho lệnh realtime
- Rate Limiting (slowapi) cho mọi endpoint
"""

import sys
import ssl
from pathlib import Path

# Đảm bảo project root nằm trong sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from server.config import (
    SERVER_HOST, SERVER_PORT, USE_HTTPS, SSL_CERTFILE, SSL_KEYFILE,
    PROJECT_ROOT, print_config, is_production,
)
from server.routers import auth, devices, policies, events, reports, requests as requests_router
from server.routers import audit as audit_router
from server.rate_limiter import setup_rate_limiting
from server.services.ws_manager import ws_manager

# ==========================================
# Tạo FastAPI app
# ==========================================
app = FastAPI(
    title="OGK Parental Control Server",
    description="Server quản lý thiết bị và chính sách cho phụ huynh",
    version="0.2.0",
    # Tắt docs ở production
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
)

# CORS - cho phép Agent và Dashboard gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: giới hạn trong production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Rate Limiting (yêu cầu 2.2: giới hạn tần suất)
# ==========================================
setup_rate_limiting(app)

# ==========================================
# Mount static files & templates
# ==========================================
STATIC_DIR = PROJECT_ROOT / "server" / "static"
TEMPLATES_DIR = PROJECT_ROOT / "server" / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ==========================================
# Include routers
# ==========================================
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(policies.router)
app.include_router(events.agent_router)
app.include_router(events.parent_router)
app.include_router(reports.router)
app.include_router(requests_router.agent_router)
app.include_router(requests_router.parent_router)
app.include_router(audit_router.router)  # NT5: con xem audit log


# ==========================================
# WebSocket - server đẩy lệnh realtime xuống Agent
# (theo yêu cầu 2.1: "WebSocket | lenh gap")
# ==========================================
@app.websocket("/ws/agent/{device_id}")
async def websocket_agent_endpoint(websocket: WebSocket, device_id: int):
    """Agent kết nối để nhận lệnh realtime từ server.

    Ví dụ lệnh:
    - {"action": "lock_now"} - khóa máy ngay
    - {"action": "policy_update", "policy": {...}} - đổi policy ngay
    - {"action": "reboot_required"} - yêu cầu restart
    """
    # TODO: xác thực qua token query param
    await ws_manager.connect(websocket, device_id)
    try:
        # Gửi hello message
        await websocket.send_json({
            "type": "hello",
            "device_id": device_id,
            "message": "Kết nối thành công. Sẵn sàng nhận lệnh.",
        })

        # Vòng lặp nhận message từ Agent
        while True:
            data = await websocket.receive_text()
            # Agent gửi ACK hoặc status update
            # Hiện tại chỉ echo để giữ connection alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, device_id)
    except Exception as e:
        print(f"[WS] Error với device {device_id}: {e}")
        ws_manager.disconnect(websocket, device_id)


# ==========================================
# Health check
# ==========================================
@app.get("/api/health")
def health():
    """Endpoint kiểm tra server còn sống không."""
    return {
        "status": "ok",
        "service": "ogk-server",
        "version": "0.2.0",
        "features": ["websocket", "rate_limit", "pagination", "https_tls12"],
        "active_websockets": ws_manager.active_count(),
    }


# ==========================================
# Trang web (HTML)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Trang chủ: chuyển hướng đến login hoặc dashboard."""
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Trang đăng nhập."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    """Trang dashboard chính."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/child/{child_id}", response_class=HTMLResponse)
def child_detail_page(request: Request, child_id: int):
    """Trang chi tiết 1 trẻ."""
    return templates.TemplateResponse("child_detail.html", {
        "request": request,
        "child_id": child_id,
    })


@app.get("/child/{child_id}/policy", response_class=HTMLResponse)
def policy_edit_page(request: Request, child_id: int):
    """Trang chỉnh sửa policy."""
    return templates.TemplateResponse("policy_edit.html", {
        "request": request,
        "child_id": child_id,
    })


@app.get("/requests", response_class=HTMLResponse)
def requests_page(request: Request):
    """Trang xem các yêu cầu từ con."""
    return templates.TemplateResponse("requests.html", {"request": request})


# ==========================================
# Khởi động
# ==========================================
def main():
    """Hàm main: chạy uvicorn."""
    import uvicorn

    print_config()
    print()

    ssl_kwargs = {}
    if USE_HTTPS:
        # Yêu cầu 2.1: TLS 1.2+ tường minh
        ssl_kwargs = {
            "ssl_certfile": SSL_CERTFILE,
            "ssl_keyfile": SSL_KEYFILE,
            "ssl_minimum_version": ssl.TLSVersion.TLSv1_2,  # ép dùng TLS 1.2+
            "ssl_ciphers": "TLSv1.2:!eNULL:!aNULL",  # chỉ dùng cipher an toàn
        }
        print(f"[HTTPS] cert: {SSL_CERTFILE}")
        print(f"[HTTPS] key:  {SSL_KEYFILE}")
        print(f"[HTTPS] TLS 1.2+ enforced")

    uvicorn.run(
        "server.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=not is_production(),
        log_level="info",
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
