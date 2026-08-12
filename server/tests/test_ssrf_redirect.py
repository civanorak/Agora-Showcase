"""Regression tests for the SSRF redirect-bypass fix (D007-R).

The original guard validated only the initial URL, then let httpx follow
redirects. A public URL that 302-redirects to an internal address (e.g. the
cloud metadata endpoint) therefore bypassed the guard entirely. safe_get /
safe_stream re-validate every hop, closing that hole.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ssrf import MAX_REDIRECTS, SSRFError, safe_get, safe_stream


def _redirect(location: str) -> MagicMock:
    r = MagicMock()
    r.status_code = 302
    r.headers = {"location": location}
    return r


def _ok() -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.headers = {}
    return r


class TestSafeGetRedirects:
    async def test_redirect_to_metadata_endpoint_is_blocked(self):
        """Public start URL 302→169.254.169.254: SSRFError raised AND — the real
        security property — the internal address is NEVER requested (validation
        runs before the GET). Asserting only 'raises' would also pass via the
        redirect cap, so we assert the URL was never handed to client.get."""
        client = MagicMock()
        client.get = AsyncMock(return_value=_redirect("http://169.254.169.254/latest/meta-data/"))
        with pytest.raises(SSRFError):
            await safe_get(client, "https://1.1.1.1/start")
        requested = [call.args[0] for call in client.get.await_args_list]
        assert all("169.254.169.254" not in u for u in requested), requested

    async def test_redirect_to_loopback_is_blocked(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=_redirect("http://127.0.0.1:8000/admin"))
        with pytest.raises(SSRFError):
            await safe_get(client, "https://1.1.1.1/")
        requested = [call.args[0] for call in client.get.await_args_list]
        assert all("127.0.0.1" not in u for u in requested), requested

    async def test_public_redirect_to_public_is_followed(self):
        # First hop redirects to another public literal, second hop is a 200.
        client = MagicMock()
        client.get = AsyncMock(side_effect=[_redirect("https://8.8.8.8/next"), _ok()])
        resp = await safe_get(client, "https://1.1.1.1/")
        assert resp.status_code == 200
        assert client.get.await_count == 2

    async def test_no_redirect_returns_response_directly(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())
        resp = await safe_get(client, "https://1.1.1.1/")
        assert resp.status_code == 200

    async def test_redirect_loop_is_capped(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=_redirect("https://1.1.1.1/loop"))
        with pytest.raises(SSRFError):
            await safe_get(client, "https://1.1.1.1/loop")
        assert client.get.await_count == MAX_REDIRECTS + 1

    async def test_get_never_follows_redirects_itself(self):
        """safe_get must call httpx with follow_redirects=False on every hop."""
        client = MagicMock()
        client.get = AsyncMock(return_value=_ok())
        await safe_get(client, "https://1.1.1.1/")
        assert client.get.await_args.kwargs["follow_redirects"] is False


class _StreamCtx:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class TestSafeStreamRedirects:
    async def test_stream_redirect_to_internal_is_blocked(self):
        client = MagicMock()
        client.stream = MagicMock(return_value=_StreamCtx(_redirect("http://169.254.169.254/")))
        with pytest.raises(SSRFError):
            async with safe_stream(client, "GET", "https://1.1.1.1/"):
                pass
        # Security property: the internal host is never streamed.
        streamed = [call.args[1] for call in client.stream.call_args_list]
        assert all("169.254.169.254" not in u for u in streamed), streamed

    async def test_stream_terminal_response_is_yielded(self):
        ok = _ok()
        client = MagicMock()
        client.stream = MagicMock(return_value=_StreamCtx(ok))
        async with safe_stream(client, "GET", "https://1.1.1.1/") as resp:
            assert resp is ok
