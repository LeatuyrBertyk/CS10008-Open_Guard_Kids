# CS10008-Parental_Control_Software

*Computer Network course project*

# 1. Overview

Platform: Agent on Windows 10/11 (x64)

Technologies and Tools: Python 3.11+, FastAPI, SQLite, SQLAlchemy, Uvicorn, pywin32/psutil

Focus: Systems and Network Programming

# 2. System architecture

```text
      MÁY CỦA TRẺ (Windows 10/11)                         MÁY CHỦ (LAN hoặc VPS lab)
+------------------------------------+               +----------------------------------+
| OGK-Agent (Python)                 |               | OGK-Server (FastAPI)             |
| +--------------------------------+ |     HTTPS     | +------------------------------+ |
| | Windows Service (SYSTEM)       | |    TLS1.2+    | | /auth  /enroll  /policy      | |
| | - Policy Enforcer              | | <-----------> | | /events  /commands           | |
| | - Screen-time Counter          | |   heartbeat   | | /reports  /audit             | |
| | - App Controller               | |      60s      | +------------------------------+ |
| | - DNS Proxy 127.0.0.1:53       | |               | | SQLite + SQLAlchemy          | |
| | - Local cache (SQLite)         | |   WebSocket   | | (policy, event, audit)       | |
| +--------------------------------+ |   lệnh gấp    | +------------------------------+ |
|                 ^                  |               +----------------------------------+
|                 |                  |                                | HTTPS
| +--------------------------------+ |                                v
| | Tray UI (quyền user)           | |               +----------------------------------+
| | - Đồng hồ còn lại              | |               | Dashboard phụ huynh (web)        |
| | - Nút 'Xin thêm giờ'           | |               | | Lịch - Báo cáo                 |
| | - Màn hình minh bạch           | |               +----------------------------------+
| +--------------------------------+ |               Cấu hình từ xa, mọi thiết bị
+------------------------------------+
  ^ named pipe / localhost
```

# 3. Installation

Make sure you have [https://www.anaconda.com/download/success?reg=skipped-miniconda](Conda) or [https://www.anaconda.com/download/success?reg=skipped-miniconda](Miniconda) installed on your system. Then, stay at the project directory and follow these steps to set up the project:

- 1. Create a virtual environment and activate it:
  
  ```bash
  conda env create -f environment.yml
  ```

  You can also check if the environment is created successfully by running:

  ```bash
  conda env list
  ```

  If you see `computer_network` in the list, it means the environment is created successfully.
- 2. Activate the environment:

  ```bash
  conda activate computer_network
  ```
