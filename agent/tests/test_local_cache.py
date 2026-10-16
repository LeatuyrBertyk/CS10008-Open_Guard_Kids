"""Test cho local cache (SQLite)."""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Thêm project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_save_and_retrieve_event(tmp_path):
    """Lưu và lấy event."""
    from agent.local_cache import LocalCache

    cache = LocalCache(db_path=tmp_path / "test.db")
    cache.save_event(
        event_type="app_start",
        app_name="chrome",
        timestamp=datetime.now(),
        client_event_id="abc-123",
    )

    pending = cache.get_pending_events()
    assert len(pending) == 1
    assert pending[0]["app_name"] == "chrome"
    assert pending[0]["event_type"] == "app_start"


def test_mark_sent(tmp_path):
    """Đánh dấu đã gửi."""
    from agent.local_cache import LocalCache

    cache = LocalCache(db_path=tmp_path / "test.db")
    eid = cache.save_event(
        event_type="web_visit",
        domain="google.com",
        timestamp=datetime.now(),
    )
    # Có 1 event chưa gửi
    assert cache.count_pending() == 1
    assert len(cache.get_pending_events()) == 1

    # mark_sent đánh dấu là sent=1
    cache.mark_sent([eid])
    # get_pending_events chỉ lấy sent=0
    assert len(cache.get_pending_events()) == 0
    # count_pending cũng chỉ đếm sent=0
    assert cache.count_pending() == 0


def test_usage_today(tmp_path):
    """Test đếm usage_today."""
    from agent.local_cache import LocalCache

    cache = LocalCache(db_path=tmp_path / "test.db")

    assert cache.get_usage_today() == 0
    cache.add_usage_minutes(15)
    assert cache.get_usage_today() == 15
    cache.add_usage_minutes(10)
    assert cache.get_usage_today() == 25


def test_state_kv(tmp_path):
    """Test set/get state."""
    from agent.local_cache import LocalCache

    cache = LocalCache(db_path=tmp_path / "test.db")
    assert cache.get_state("my_key") is None

    cache.set_state("my_key", {"a": 1, "b": "hello"})
    assert cache.get_state("my_key") == {"a": 1, "b": "hello"}

    cache.set_state("my_key", [1, 2, 3])
    assert cache.get_state("my_key") == [1, 2, 3]
