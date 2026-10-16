"""Test cho allowlist: domain và process."""

import pytest
from shared.allowlist import is_domain_allowed, is_process_allowed


class TestDomainAllowlist:
    """Test domain allowlist."""

    def test_111vn_allowed(self):
        assert is_domain_allowed("111.vn") is True

    def test_gov_vn_allowed(self):
        assert is_domain_allowed("cantho.gov.vn") is True

    def test_edu_vn_allowed(self):
        assert is_domain_allowed("school.edu.vn") is True

    def test_facebook_blocked(self):
        assert is_domain_allowed("facebook.com") is False

    def test_www_prefix_normalized(self):
        """www.facebook.com cũng bị chặn (sau khi strip www.)."""
        assert is_domain_allowed("www.facebook.com") is False

    def test_empty_domain_allowed(self):
        """Domain rỗng → cho phép (không filter)."""
        assert is_domain_allowed("") is True

    def test_windows_update_allowed(self):
        assert is_domain_allowed("windowsupdate.microsoft.com") is True


class TestProcessAllowlist:
    """Test process allowlist."""

    def test_system_allowed(self):
        assert is_process_allowed("System") is True

    def test_svchost_allowed(self):
        assert is_process_allowed("svchost.exe") is True

    def test_msmpeng_allowed(self):
        """Windows Defender KHÔNG BAO GIỜ được chặn."""
        assert is_process_allowed("MsMpEng.exe") is True

    def test_explorer_allowed(self):
        assert is_process_allowed("explorer.exe") is True

    def test_chrome_not_in_allowlist(self):
        """Chrome không có sẵn trong allowlist."""
        assert is_process_allowed("chrome.exe") is False
