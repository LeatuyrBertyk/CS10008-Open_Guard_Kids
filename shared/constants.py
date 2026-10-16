"""Hằng số dùng chung cho toàn project.

Tập trung tất cả magic numbers và chuỗi cố định ở đây,
giúp dễ bảo trì và thay đổi.
"""

# ==========================================
# Phiên bản ứng dụng
# ==========================================
APP_NAME = "OGK Parental Control"
APP_VERSION = "0.1.0"

# ==========================================
# Cấu hình Server mặc định
# ==========================================
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8000
# URL gốc của server, dùng cho cả HTTP API và Dashboard
# Trong triển khai thật nên dùng HTTPS
DEFAULT_SERVER_URL = f"http://{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}"

# ==========================================
# Heartbeat
# ==========================================
# Khoảng thời gian Agent gửi heartbeat (giây)
# 60s là yêu cầu từ giáo viên trong file yêu cầu
HEARTBEAT_INTERVAL_SECONDS = 60

# Số lần retry khi gọi API thất bại
HEARTBEAT_RETRY_TIMES = 3

# Timeout cho mỗi request (giây)
REQUEST_TIMEOUT_SECONDS = 10

# ==========================================
# Rate Limiting (yêu cầu 2.2: giới hạn tần suất)
# ==========================================
RATE_LIMIT_DEFAULT = "100/minute"       # mặc định cho mọi endpoint
RATE_LIMIT_LOGIN = "5/minute"           # chống brute-force
RATE_LIMIT_HEARTBEAT = "2/minute"       # chỉ cần 1/phút
RATE_LIMIT_ENROLL = "3/hour"            # enroll hiếm khi
RATE_LIMIT_EVENTS = "30/minute"         # batch events
RATE_LIMIT_REQUESTS = "10/minute"       # con tạo request

# ==========================================
# Pagination (yêu cầu 2.2: phân trang)
# ==========================================
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ==========================================
# Local cache (khi mất mạng)
# ==========================================
# Số sự kiện tối đa lưu trong SQLite local
MAX_LOCAL_EVENTS = 10000

# Kích thước batch khi flush lên server
EVENT_FLUSH_BATCH_SIZE = 50

# Khoảng thời gian flush queue (giây)
EVENT_FLUSH_INTERVAL_SECONDS = 30

# ==========================================
# Screen time
# ==========================================
# Khoảng thời gian kiểm tra session active (giây)
SCREENTIME_CHECK_INTERVAL = 30

# Ngưỡng idle (giây) - nếu không có thao tác trong khoảng này thì tính là idle
IDLE_THRESHOLD_SECONDS = 120

# ==========================================
# App Controller
# ==========================================
# Khoảng thời gian quét tiến trình (giây)
APP_SCAN_INTERVAL = 2

# Thời gian chờ trước khi kill process (giây) - cho phép user save
APP_KILL_GRACE_PERIOD = 3

# ==========================================
# DNS Proxy
# ==========================================
# Cổng DNS proxy lắng nghe (port 53 là cổng DNS chuẩn)
DNS_PROXY_PORT = 53

# DNS upstream (Google Public DNS)
DNS_UPSTREAM_HOST = "8.8.8.8"
DNS_UPSTREAM_PORT = 53

# ==========================================
# Local IPC (Service ↔ Tray UI)
# ==========================================
# HTTP localhost cho Tray UI gọi Service
LOCAL_IPC_HOST = "127.0.0.1"
LOCAL_IPC_PORT = 9999

# Đường dẫn file token cục bộ (cả 2 bên đọc để xác thực)
LOCAL_TOKEN_FILE = "local_token.txt"

# ==========================================
# Đường dẫn file
# ==========================================
AGENT_CONFIG_FILE = "agent/config.json"
AGENT_LOCAL_DB = "agent/local_cache.db"
SERVER_DB_FILE = "server/ogk.db"
SERVER_LOG_FILE = "server/server.log"
AGENT_LOG_FILE = "agent/agent.log"
TRAY_STATE_FILE = "agent/tray_state.json"

# ==========================================
# Roles
# ==========================================
ROLE_PARENT = "parent"
ROLE_ADMIN = "admin"

# ==========================================
# Loại sự kiện
# ==========================================
EVENT_APP_START = "app_start"
EVENT_APP_END = "app_end"
EVENT_APP_BLOCKED = "app_blocked"
EVENT_WEB_VISIT = "web_visit"
EVENT_WEB_BLOCKED = "web_blocked"
EVENT_LOCK_SCREEN = "lock_screen"
EVENT_UNLOCK = "unlock"
EVENT_REQUEST_EXTRA_TIME = "request_extra_time"
EVENT_REPORT_FALSE_BLOCK = "report_false_block"

# ==========================================
# Trạng thái yêu cầu
# ==========================================
REQUEST_PENDING = "pending"
REQUEST_APPROVED = "approved"
REQUEST_REJECTED = "rejected"
