"""Tests for the email-capture leads API."""

import pytest

from app.config import settings
from app.db import get_db


@pytest.mark.asyncio
async def test_capture_lead_valid(client):
    resp = await client.post(
        "/leads",
        json={"email": "merchant@store.com", "url": "https://store.com", "coverage_pct": 9.7},
    )
    assert resp.status_code == 201
    assert resp.json() == {"status": "ok"}

    db = await get_db()
    cursor = await db.execute("SELECT email, url, coverage_pct FROM leads")
    row = await cursor.fetchone()
    assert row["email"] == "merchant@store.com"
    assert row["url"] == "https://store.com"
    assert row["coverage_pct"] == 9.7


@pytest.mark.asyncio
async def test_capture_lead_invalid_email(client):
    resp = await client.post(
        "/leads",
        json={"email": "not-an-email", "url": "https://store.com"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_capture_lead_without_coverage(client):
    resp = await client.post(
        "/leads",
        json={"email": "merchant@store.com", "url": "https://store.com"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_capture_lead_rejects_non_http_url(client):
    resp = await client.post(
        "/leads",
        json={"email": "merchant@store.com", "url": "javascript:alert(1)"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_capture_lead_rejects_oversized_url(client):
    resp = await client.post(
        "/leads",
        json={"email": "merchant@store.com", "url": "https://store.com/" + "a" * 3000},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_capture_lead_rejects_out_of_range_coverage(client):
    resp = await client.post(
        "/leads",
        json={"email": "merchant@store.com", "url": "https://store.com", "coverage_pct": 250},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_leads_requires_admin_token(client):
    resp = await client.get("/leads")
    assert resp.status_code == 404  # admin_token unset in tests by default


@pytest.mark.asyncio
async def test_list_leads_rejects_wrong_token(client):
    settings.admin_token = "secret"
    try:
        resp = await client.get("/leads", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 403
    finally:
        settings.admin_token = ""


@pytest.mark.asyncio
async def test_list_leads_sorted_worst_gap_first(client):
    settings.admin_token = "secret"
    try:
        await client.post("/leads", json={"email": "a@store.com", "url": "https://a.com", "coverage_pct": 80})
        await client.post("/leads", json={"email": "b@store.com", "url": "https://b.com", "coverage_pct": 10})
        await client.post("/leads", json={"email": "c@store.com", "url": "https://c.com"})

        resp = await client.get("/leads", headers={"Authorization": "Bearer secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert [row["email"] for row in data] == ["b@store.com", "a@store.com", "c@store.com"]
    finally:
        settings.admin_token = ""
