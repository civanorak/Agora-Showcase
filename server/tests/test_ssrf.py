"""Tests for the SSRF guard on user-supplied audit URLs."""

import pytest

from app.ssrf import SSRFError, _is_public_ip, validate_public_url


class TestIsPublicIp:
    def test_public_v4_is_public(self):
        assert _is_public_ip("93.184.216.34") is True  # example.com

    def test_loopback_v4_rejected(self):
        assert _is_public_ip("127.0.0.1") is False

    def test_private_v4_rejected(self):
        for ip in ("10.0.0.5", "192.168.1.1", "172.16.0.1"):
            assert _is_public_ip(ip) is False

    def test_link_local_metadata_rejected(self):
        # AWS/GCP cloud metadata endpoint — the classic SSRF target.
        assert _is_public_ip("169.254.169.254") is False

    def test_loopback_v6_rejected(self):
        assert _is_public_ip("::1") is False

    def test_ipv4_mapped_v6_loopback_rejected(self):
        assert _is_public_ip("::ffff:127.0.0.1") is False


class TestValidatePublicUrl:
    async def test_bare_scheme_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("ftp://example.com")

    async def test_localhost_literal_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("http://127.0.0.1:8000/admin")

    async def test_private_literal_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("http://192.168.0.10/")

    async def test_metadata_literal_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("http://169.254.169.254/latest/meta-data/")

    async def test_unresolvable_host_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("http://this-host-does-not-exist.invalid/")

    async def test_no_host_rejected(self):
        with pytest.raises(SSRFError):
            await validate_public_url("http:///path-only")

    async def test_public_literal_allowed(self):
        # 1.1.1.1 (Cloudflare) is globally routable; no DNS needed.
        await validate_public_url("https://1.1.1.1/")
