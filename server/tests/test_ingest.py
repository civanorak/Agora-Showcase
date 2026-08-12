"""Tests for the ingest API."""

import pytest






@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_ingest_missing_auth(client):
    resp = await client.post(
        "/ingest",
        json={
            "method": "GET",
            "path": "/test",
            "status": 200,
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_valid_event(client):
    resp = await client.post(
        "/ingest",
        json={
            "method": "GET",
            "path": "/products/laptop",
            "status": 200,
            "user_agent": "GPTBot/1.0",
            "site_id": "00000000-0000-0000-0000-000000000001",
        },
        headers={"Authorization": "Bearer demo-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["event_id"] is not None


@pytest.mark.asyncio
async def test_ingest_accepts_collector_string_site_id(client):
    """Real collectors send their configured site_id as a plain string
    (e.g. "demo-site", token_hex ids from /sites) — never a UUID.
    The server derives the site from the API key, so any string must be accepted."""
    resp = await client.post(
        "/ingest",
        json={
            "method": "GET",
            "path": "/products/laptop",
            "status": 200,
            "user_agent": "GPTBot/1.0",
            "site_id": "demo-site",
        },
        headers={"Authorization": "Bearer demo-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_ingest_invalid_status(client):
    resp = await client.post(
        "/ingest",
        json={
            "method": "GET",
            "path": "/test",
            "status": 999,
        },
        headers={"Authorization": "Bearer demo-key"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_llms_txt_demo_mode(client):
    from app.config import settings
    from app.db import get_db
    import hashlib

    original_demo_mode = settings.demo_mode
    settings.demo_mode = True
    try:
        db = await get_db()
        key_hash = hashlib.sha256(b"demo-key").hexdigest()
        await db.execute(
            "INSERT OR IGNORE INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
            ("demo-site", "Demo Store", key_hash),
        )
        await db.commit()

        resp = await client.get("/llms.txt", headers={"User-Agent": "PerplexityBot/1.0"})
        assert resp.status_code == 200
        assert "AGORA Demo Store" in resp.text

        cursor = await db.execute(
            """
            SELECT e.path, c.verdict
            FROM events e
            JOIN classifications c ON c.event_id = e.id
            WHERE e.site_id = 'demo-site' AND e.path = '/llms.txt'
            ORDER BY e.id DESC LIMIT 1
            """
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["path"] == "/llms.txt"
        assert row["verdict"] == "crawler_search"
    finally:
        settings.demo_mode = original_demo_mode


@pytest.mark.asyncio
async def test_llms_txt_production_mode(client):
    from app.config import settings
    from app.db import get_db

    original_demo_mode = settings.demo_mode
    settings.demo_mode = False
    try:
        db = await get_db()
        cursor = await db.execute("SELECT COUNT(*) AS count FROM events")
        before_count = (await cursor.fetchone())["count"]

        resp = await client.get("/llms.txt", headers={"User-Agent": "PerplexityBot/1.0"})
        assert resp.status_code == 200
        assert "AGORA Demo Store" in resp.text

        cursor = await db.execute("SELECT COUNT(*) AS count FROM events")
        after_count = (await cursor.fetchone())["count"]
        assert before_count == after_count
    finally:
        settings.demo_mode = original_demo_mode


@pytest.mark.asyncio
async def test_llms_txt_always_serves_text_plain(client):
    resp = await client.get("/llms.txt", headers={"User-Agent": "ChatGPT-User/1.0", "Accept": "text/html"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "AGORA Demo Store" in resp.text


@pytest.mark.asyncio
async def test_simulate_bot_visit(client):
    from app.config import settings
    from app.db import get_db

    original_demo_mode = settings.demo_mode
    settings.demo_mode = True
    try:
        db = await get_db()
        # Verify that we can simulate ChatGPT
        resp = await client.post("/events/simulate?agent=chatgpt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["verdict"] == "assistant_browse"

        # Verify database record exists
        cursor = await db.execute(
            """
            SELECT e.path, c.verdict
            FROM events e
            JOIN classifications c ON c.event_id = e.id
            WHERE e.id = ?
            """,
            (data["event_id"],),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["path"] == "/llms.txt"
        assert row["verdict"] == "assistant_browse"

        # Verify that we cannot simulate invalid agent profile
        resp = await client.post("/events/simulate?agent=invalid_agent")
        assert resp.status_code == 400
    finally:
        settings.demo_mode = original_demo_mode


@pytest.mark.asyncio
async def test_simulate_bot_visit_production_mode(client):
    from app.config import settings

    original_demo_mode = settings.demo_mode
    settings.demo_mode = False
    try:
        # Verify that simulate returns 404 in production mode
        resp = await client.post("/events/simulate?agent=chatgpt")
        assert resp.status_code == 404
    finally:
        settings.demo_mode = original_demo_mode
