import pytest
from httpx import ASGITransport, AsyncClient
import hashlib

from app.main import app
from app.db import get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_report_preview_invalid_site(client):
    # Query with non-existent site
    resp = await client.get("/report/preview?site_id=non-existent-site-id-12345")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Site not found"


@pytest.mark.asyncio
async def test_report_preview_ok(client):
    db = await get_db()
    # Insert site "demo-site"
    key_hash = hashlib.sha256(b"demo-key").hexdigest()
    await db.execute(
        "INSERT OR IGNORE INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
        ("demo-site", "Demo Store", key_hash),
    )
    # Insert some dummy events to make sure queries work
    await db.execute(
        """
        INSERT INTO events (site_id, ts, method, path, status, ua, ip_hash, headers, beacon_seen)
        VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'GET', '/products', 200, 'GPTBot/1.0', 'hash', '{}', 0)
        """,
        ("demo-site",),
    )
    event_id = 1
    # Check lastrowid or insert a classification manually
    cursor = await db.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    row = await cursor.fetchone()
    if row:
        event_id = row["id"]

    await db.execute(
        """
        INSERT OR IGNORE INTO classifications (event_id, verdict, confidence, evidence, signature_id)
        VALUES (?, 'crawler_training', 0.9, '[]', 'gptbot')
        """,
        (event_id,),
    )
    await db.commit()

    resp = await client.get("/report/preview?site_id=demo-site")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "AGORA Weekly AI Traffic Report" in resp.text
    assert "Demo Store" in resp.text


@pytest.mark.asyncio
async def test_report_pdf_redirects_to_html_preview(client):
    """D005: PDF was dropped; /report/pdf now 308-redirects to the HTML report."""
    resp = await client.get(
        "/report/pdf?site_id=demo-site", follow_redirects=False
    )
    assert resp.status_code == 308
    assert resp.headers["location"] == "/report/preview?site_id=demo-site"
