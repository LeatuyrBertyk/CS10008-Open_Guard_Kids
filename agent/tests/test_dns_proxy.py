"""Test cho DNS proxy resolver logic."""

import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_blocked_domain():
    """Domain trong blacklist bị chặn."""
    from agent.dns_proxy import FilteringResolver
    from agent.events import EventQueue
    from unittest.mock import MagicMock

    mock_queue = MagicMock(spec=EventQueue)
    resolver = FilteringResolver(mock_queue)
    resolver.update_policy(blocked_domains=["facebook.com", "tiktok.com"])

    assert resolver._is_blocked("facebook.com") is True
    assert resolver._is_blocked("tiktok.com") is True
    assert resolver._is_blocked("subdomain.facebook.com") is True


def test_allowed_domain():
    """Domain trong allowlist mặc định KHÔNG bị chặn."""
    from agent.dns_proxy import FilteringResolver
    from agent.events import EventQueue
    from unittest.mock import MagicMock

    mock_queue = MagicMock(spec=EventQueue)
    resolver = FilteringResolver(mock_queue)
    resolver.update_policy(blocked_domains=["facebook.com"])

    # 111 và gov.vn được phép
    assert resolver._is_blocked("111.vn") is False
    assert resolver._is_blocked("cantho.gov.vn") is False
    assert resolver._is_blocked("school.edu.vn") is False


def test_locked_mode_blocks_everything():
    """Khi khóa máy, chỉ allowlist hoạt động."""
    from agent.dns_proxy import FilteringResolver
    from agent.events import EventQueue
    from unittest.mock import MagicMock

    mock_queue = MagicMock(spec=EventQueue)
    resolver = FilteringResolver(mock_queue)
    resolver.update_policy(blocked_domains=["facebook.com"])
    resolver.set_locked(True)

    # Mọi thứ đều bị chặn, TRỪ allowlist
    assert resolver._is_blocked("facebook.com") is True
    assert resolver._is_blocked("google.com") is True  # không có trong allowlist
    assert resolver._is_blocked("111.vn") is False  # có trong allowlist


def test_extra_allowed_domains():
    """Domain được thêm vào allowed_domains từ policy."""
    from agent.dns_proxy import FilteringResolver
    from agent.events import EventQueue
    from unittest.mock import MagicMock

    mock_queue = MagicMock(spec=EventQueue)
    resolver = FilteringResolver(mock_queue)
    resolver.update_policy(
        blocked_domains=["all-social.com"],
        allowed_domains=["wikipedia.org"],
    )

    assert resolver._is_blocked("wikipedia.org") is False
    assert resolver._is_blocked("all-social.com") is True
