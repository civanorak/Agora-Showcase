"""Tests for the ASGI collector middleware."""

import pytest

from agora_collector.middleware import AGORACollector


class FakeApp:
    """Minimal ASGI app for testing."""

    def __init__(self):
        self.called = False
        self.scope_seen = None

    async def __call__(self, scope, receive, send):
        self.called = True
        self.scope_seen = scope
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


async def fake_receive():
    return {"type": "http.request"}


async def fake_send(msg):
    pass


@pytest.mark.asyncio
async def test_middleware_passes_through():
    """Middleware must never block the upstream app."""
    fake = FakeApp()
    middleware = AGORACollector(
        fake,
        api_url="http://localhost:9999",
        api_key="test",
        site_id="test-site",
    )

    scope = {"type": "http", "method": "GET", "path": "/products/laptop", "headers": []}
    await middleware(scope, fake_receive, fake_send)

    assert fake.called, "Upstream app must be called even if AGORA fails"


@pytest.mark.asyncio
async def test_middleware_ignores_static_paths():
    """Static asset paths should not be captured."""
    fake = FakeApp()
    middleware = AGORACollector(
        fake,
        api_url="http://localhost:9999",
        api_key="test",
        site_id="test-site",
    )

    # Should still pass through to upstream
    scope = {"type": "http", "method": "GET", "path": "/static/logo.png", "headers": []}
    await middleware(scope, fake_receive, fake_send)

    assert fake.called


@pytest.mark.asyncio
async def test_middleware_extracts_ua():
    """User agent should be extracted from headers."""
    fake = FakeApp()
    middleware = AGORACollector(
        fake,
        api_url="http://localhost:9999",
        api_key="test",
        site_id="test-site",
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"user-agent", b"GPTBot/1.0")],
    }
    event = middleware._extract_event(scope, {})
    assert event["user_agent"] == "GPTBot/1.0"


@pytest.mark.asyncio
async def test_middleware_captures_real_response_status():
    """Event must carry the status the merchant app actually returned, not a hardcoded 200."""

    class NotFoundApp(FakeApp):
        async def __call__(self, scope, receive, send):
            self.called = True
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"missing"})

    fake = NotFoundApp()
    middleware = AGORACollector(
        fake,
        api_url="http://localhost:9999",
        api_key="test",
        site_id="test-site",
    )

    captured: list[dict] = []

    async def spy_send_event(event):
        captured.append(event)
        return True

    middleware._send_event = spy_send_event

    scope = {"type": "http", "method": "GET", "path": "/products/gone", "headers": []}
    await middleware(scope, fake_receive, fake_send)
    # The ingest send is fired as a task after the response; let it run.
    import asyncio

    await asyncio.sleep(0)

    assert fake.called
    assert len(captured) == 1
    assert captured[0]["status"] == 404


@pytest.mark.asyncio
async def test_middleware_ignores_non_http():
    """Non-HTTP scopes should pass through untouched."""
    fake = FakeApp()
    middleware = AGORACollector(
        fake,
        api_url="http://localhost:9999",
        api_key="test",
        site_id="test-site",
    )

    scope = {"type": "lifespan"}
    await middleware(scope, fake_receive, fake_send)
    assert fake.called
