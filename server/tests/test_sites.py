"""Tests for the admin-gated sites API."""

import hashlib

import pytest

from app.config import settings
from app.db import get_db


@pytest.mark.asyncio
async def test_create_site_requires_admin_token(client):
    resp = await client.post("/sites", json={"name": "Acme Store"})
    assert resp.status_code == 404  # admin_token unset in tests by default


@pytest.mark.asyncio
async def test_create_site_rejects_wrong_token(client):
    settings.admin_token = "secret"
    try:
        resp = await client.post(
            "/sites",
            json={"name": "Acme Store"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 403
    finally:
        settings.admin_token = ""


@pytest.mark.asyncio
async def test_create_site_returns_plaintext_key_but_stores_hash(client):
    settings.admin_token = "secret"
    try:
        resp = await client.post(
            "/sites",
            json={"name": "Acme Store"},
            headers={"Authorization": "Bearer secret"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Store"
        assert data["id"]
        raw_key = data["api_key"]
        assert raw_key

        # The plaintext key must never be persisted — only its SHA-256 hash.
        db = await get_db()
        cursor = await db.execute(
            "SELECT api_key_hash FROM sites WHERE id = ?", (data["id"],)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["api_key_hash"] == hashlib.sha256(raw_key.encode()).hexdigest()
        assert row["api_key_hash"] != raw_key
    finally:
        settings.admin_token = ""


@pytest.mark.asyncio
async def test_create_site_invalid_body(client):
    settings.admin_token = "secret"
    try:
        resp = await client.post(
            "/sites",
            json={},  # missing required "name"
            headers={"Authorization": "Bearer secret"},
        )
        assert resp.status_code == 422
    finally:
        settings.admin_token = ""


@pytest.mark.asyncio
async def test_list_sites_requires_admin_token(client):
    resp = await client.get("/sites")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_sites_returns_event_counts(client):
    settings.admin_token = "secret"
    try:
        db = await get_db()
        await db.execute(
            "INSERT INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
            ("site-a", "Alpha Store", "hash-a"),
        )
        await db.execute(
            "INSERT INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
            ("site-b", "Bravo Store", "hash-b"),
        )
        # Two events for Alpha, none for Bravo — exercises the LEFT JOIN COUNT.
        for path in ("/products/1", "/products/2"):
            await db.execute(
                "INSERT INTO events (site_id, method, path, status) VALUES (?, 'GET', ?, 200)",
                ("site-a", path),
            )
        await db.commit()

        resp = await client.get("/sites", headers={"Authorization": "Bearer secret"})
        assert resp.status_code == 200
        data = resp.json()
        # Ordered by name: Alpha before Bravo.
        assert [s["name"] for s in data] == ["Alpha Store", "Bravo Store"]
        counts = {s["id"]: s["event_count"] for s in data}
        assert counts == {"site-a": 2, "site-b": 0}
    finally:
        settings.admin_token = ""
