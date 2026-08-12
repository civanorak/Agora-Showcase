"""Auth gating for dashboard read endpoints (/events, /events/stream, /stats).

Open in demo mode, admin-gated on a public host (demo off). See D007-adjacent
gating decision and app/auth.py::require_read_access.
"""

import pytest

from app.config import settings


@pytest.fixture
def prod_mode():
    """Run a test as if hosted publicly: demo off, admin token configured."""
    prev_demo, prev_token = settings.demo_mode, settings.admin_token
    settings.demo_mode = False
    settings.admin_token = "secret-admin"
    yield
    settings.demo_mode = prev_demo
    settings.admin_token = prev_token


@pytest.mark.asyncio
async def test_events_open_in_demo_mode(client):
    # client fixture sets demo_mode=True → no auth needed
    resp = await client.get("/events")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stats_open_in_demo_mode(client):
    resp = await client.get("/stats?site_id=demo-site")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_rejected_without_token_in_prod(client, prod_mode):
    resp = await client.get("/events")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_rejected_without_token_in_prod(client, prod_mode):
    resp = await client.get("/stats?site_id=demo-site")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_events_allowed_with_admin_token_in_prod(client, prod_mode):
    resp = await client.get(
        "/events", headers={"Authorization": "Bearer secret-admin"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stats_allowed_with_admin_token_in_prod(client, prod_mode):
    resp = await client.get(
        "/stats?site_id=demo-site",
        headers={"Authorization": "Bearer secret-admin"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_stream_rejected_without_token_in_prod(client, prod_mode):
    resp = await client.get("/events/stream")
    assert resp.status_code == 403
