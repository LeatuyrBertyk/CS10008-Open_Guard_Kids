"""Danh sách miễn chặn vĩnh viễn (theo nguyên tắc NT6 - An toàn).

Đây là danh sách QUAN TRỌNG, được tích hợp vào mọi nơi có chặn.
Nguyên tắc: khi hết giờ, khóa máy, hoặc bất kỳ luật nào,
những domain và process dưới đây LUÔN được phép hoạt động.

Lý do: trẻ có thể cần gọi cứu hỏa, gọi 111, hoặc vào web trường
trong tình huống khẩn cấp - phần mềm không được phép cản trở.
"""

# ==========================================
# Domain miễn chặn vĩnh viễn
# ==========================================
# Theo yêu cầu giáo viên (mục NT6):
# - Cổng thông tin trường học
# - Tổng đài quốc gia bảo vệ trẻ em 111
# - Dịch vụ cứu hộ khẩn cấp

# Format: domain phải khớp chính xác (case-insensitive)
# Có thể dùng suffix match: nếu domain kết thúc bằng ".gov.vn" thì cả miền con cũng được phép
ALLOWED_DOMAINS_EXACT: set[str] = {
    # Tổng đài bảo vệ trẻ em
    "111.vn",
    "tongdai111.vn",
    "childfund.org.vn",

    # Cứu hỏa / cứu thương (một số dịch vụ có web)
    "cuuhoa.vn",
    "115.vn",  # Cấp cứu y tế

    # Một số dịch vụ cứu nạn phổ biến
    "redcross.org.vn",
    "who.int",  # Tổ chức y tế thế giới (tra cứu thông tin y tế)
}

# Domain suffix - cả miền con cũng được phép
# Ví dụ: nếu có ".gov.vn" thì "cantho.gov.vn" cũng OK
ALLOWED_DOMAINS_SUFFIX: set[str] = {
    ".gov.vn",       # Cổng thông tin chính phủ và các cơ quan nhà nước
    ".edu.vn",       # Tên miền giáo dục Việt Nam
    # Lưu ý: thêm ".edu.vn" có thể cho phép sinh viên vào web trường
    # trong mọi tình huống, kể cả khi "hết giờ" - đây là chủ ý.
    ".edu",
    # Các trang tìm kiếm lớn - KHÔNG bắt buộc, có thể bỏ nếu muốn chặt
    # "google.com",
}

# Domain đặc biệt của Microsoft Windows Update - cần thiết để máy hoạt động ổn định
ALLOWED_DOMAINS_WINDOWS: set[str] = {
    "windowsupdate.microsoft.com",
    "update.microsoft.com",
    "download.windowsupdate.com",
    "microsoft.com",
}


def is_domain_allowed(domain: str) -> bool:
    """Kiểm tra domain có nằm trong allowlist không.

    Args:
        domain: tên miền cần kiểm tra, ví dụ "facebook.com"

    Returns:
        True nếu domain được phép (nằm trong allowlist)
    """
    if not domain:
        return True  # domain rỗng thì bỏ qua

    domain_lower = domain.lower().strip()

    # Bỏ www. phía trước để so sánh công bằng
    if domain_lower.startswith("www."):
        domain_lower = domain_lower[4:]

    # So khớp chính xác
    if domain_lower in ALLOWED_DOMAINS_EXACT:
        return True

    if domain_lower in ALLOWED_DOMAINS_WINDOWS:
        return True

    # So khớp suffix (cả miền con)
    for suffix in ALLOWED_DOMAINS_SUFFIX:
        if domain_lower.endswith(suffix):
            return True

    return False


# ==========================================
# Process miễn chặn vĩnh viễn
# ==========================================
# Theo yêu cầu NT4: Không được giả vờ lỗi mạng
# Theo yêu cầu NT6: An toàn có ưu tiên tuyệt đối
# → KHÔNG BAO GIỜ chặn các process hệ thống và ứng dụng khẩn cấp

# Tên process (không bao gồm .exe, chữ thường)
ALLOWED_PROCESSES: set[str] = {
    # Hệ thống Windows - không bao giờ đụng vào
    "system",
    "system idle process",
    "svchost",
    "lsass",
    "csrss",
    "wininit",
    "services",
    "winlogon",
    "dwm",
    "explorer",  # Windows Explorer - nếu tắt thì mất desktop
    "taskmgr",
    "taskhost",
    "taskhostw",
    "sihost",
    "fontdrvhost",
    "wmiprvse",
    "spoolsv",
    "audiodg",

    # Windows Security & Defender
    "msmpeng",        # Windows Defender
    "securityhealthservice",
    "securityhealthhost",

    # Windows Update
    "wuauserv",
    "bits",           # Background Intelligent Transfer Service

    # Ứng dụng Settings của Windows
    "systemsettings",
    "lockapp",        # Màn hình khóa
    "logonui",

    # Đồng hồ, lịch, weather
    "shellexperiencehost",
    "runtimebroker",

    # Tổng đài khẩn cấp (thường là edge/chrome nhưng cho phép gọi qua web)
    # Không cần thêm vì là domain, không phải process
}


def is_process_allowed(process_name: str) -> bool:
    """Kiểm tra process có nằm trong allowlist không.

    Args:
        process_name: tên process, ví dụ "chrome.exe" hoặc "chrome"

    Returns:
        True nếu process KHÔNG BAO GIỜ được chặn
    """
    if not process_name:
        return True

    # Bỏ .exe nếu có
    name = process_name.lower().strip()
    if name.endswith(".exe"):
        name = name[:-4]

    return name in ALLOWED_PROCESSES
