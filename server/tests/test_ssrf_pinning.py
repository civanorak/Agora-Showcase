"""Regression tests for DNS-rebinding pinning.

The redirect fix (D007-R) re-validated every hop, but each hop still let httpx
re-resolve the hostname at connect time. An attacker with a low-TTL DNS server
could answer our validation lookup with a public IP and the real connect with a
private one (TOCTOU). The guard now pins the connection to the exact IP it
validated and hands httpx that IP literal, so no second resolution happens.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app import ssrf
from app.ssrf import SSRFError, pinned_get, safe_get


def _ok() -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.headers = {}
    return r


class TestPinning:
    async def test_request_targets_resolved_ip_not_hostname(self, monkeypatch):
        """The URL handed to httpx must carry the validated IP literal — not the
        hostname — so httpx cannot re-resolve it to an internal address."""
        async def fake_resolve(host, port):
            return ["93.184.216.34"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        await safe_get(client, "https://example.com/path?q=1")

        called_url = client.get.await_args.args[0]
        assert "93.184.216.34" in called_url
        assert "example.com" not in called_url
        assert "/path?q=1" in called_url

    async def test_original_host_and_sni_preserved(self, monkeypatch):
        """Virtual hosting + TLS cert verification must still work: the original
        hostname rides along as the Host header and the SNI override."""
        async def fake_resolve(host, port):
            return ["93.184.216.34"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        await safe_get(client, "https://example.com/")

        kwargs = client.get.await_args.kwargs
        assert kwargs["headers"]["Host"] == "example.com"
        assert kwargs["extensions"]["sni_hostname"] == "example.com"

    async def test_rebinding_to_internal_ip_is_refused(self, monkeypatch):
        """If the hostname resolves to a private address, no request is made."""
        async def fake_resolve(host, port):
            return ["169.254.169.254"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        with pytest.raises(SSRFError):
            await safe_get(client, "https://rebind.evil/")
        client.get.assert_not_awaited()

    async def test_split_answer_with_one_internal_ip_is_refused(self, monkeypatch):
        """A/AAAA split trick: one public, one internal → the whole URL is refused."""
        async def fake_resolve(host, port):
            return ["93.184.216.34", "10.0.0.5"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        with pytest.raises(SSRFError):
            await safe_get(client, "https://split.evil/")
        client.get.assert_not_awaited()

    async def test_plain_http_has_no_sni_override(self, monkeypatch):
        """SNI is a TLS concept — no override for http:// URLs."""
        async def fake_resolve(host, port):
            return ["93.184.216.34"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        await safe_get(client, "http://example.com/")

        assert "extensions" not in client.get.await_args.kwargs

    async def test_ip_literal_url_is_not_rewritten(self):
        """A URL that is already an IP literal needs no pin and keeps its form."""
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        await pinned_get(client, "https://1.1.1.1/x")

        assert client.get.await_args.args[0] == "https://1.1.1.1/x"
        assert "extensions" not in client.get.await_args.kwargs

    async def test_pinned_get_does_not_follow_redirects(self, monkeypatch):
        async def fake_resolve(host, port):
            return ["93.184.216.34"]

        monkeypatch.setattr(ssrf, "_resolve", fake_resolve)
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())

        await pinned_get(client, "https://example.com/")

        assert client.get.await_args.kwargs["follow_redirects"] is False
