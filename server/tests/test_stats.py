"""Tests for the stats aggregation API."""

import pytest

from app.db import get_db

SITE_ID = "stats-site"


async def _seed_event(db, *, path: str, verdict: str, hours_ago: int) -> None:
    """Insert an event + its classification at a given age (hours in the past)."""
    cursor = await db.execute(
        """
        INSERT INTO events (site_id, ts, method, path, status)
        VALUES (?, datetime('now', ?), 'GET', ?, 200)
        """,
        (SITE_ID, f"-{hours_ago} hours", path),
    )
    event_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO classifications (event_id, verdict, confidence) VALUES (?, ?, 1.0)",
        (event_id, verdict),
    )


@pytest.mark.asyncio
async def test_stats_requires_site_id(client):
    resp = await client.get("/stats")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stats_empty_site_returns_zeroed_shape(client):
    resp = await client.get("/stats", params={"site_id": SITE_ID})
    assert resp.status_code == 200
    data = resp.json()
    assert data["site_id"] == SITE_ID
    assert data["window"] == "24h"
    assert data["verdict_counts"] == {}
    assert data["top_paths"] == []
    assert data["hourly_buckets"] == []


@pytest.mark.asyncio
async def test_stats_aggregates_verdicts_and_paths(client):
    db = await get_db()
    await _seed_event(db, path="/llms.txt", verdict="crawler_search", hours_ago=1)
    await _seed_event(db, path="/llms.txt", verdict="crawler_search", hours_ago=2)
    await _seed_event(db, path="/products/1", verdict="assistant_browse", hours_ago=1)
    await db.commit()

    resp = await client.get("/stats", params={"site_id": SITE_ID})
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict_counts"] == {"crawler_search": 2, "assistant_browse": 1}
    top = {p["path"]: p["count"] for p in data["top_paths"]}
    assert top == {"/llms.txt": 2, "/products/1": 1}
    # top_paths is ordered by count DESC.
    assert data["top_paths"][0]["path"] == "/llms.txt"
    assert len(data["hourly_buckets"]) >= 1


@pytest.mark.asyncio
async def test_stats_window_excludes_older_events(client):
    db = await get_db()
    await _seed_event(db, path="/recent", verdict="crawler_search", hours_ago=1)
    await _seed_event(db, path="/old", verdict="crawler_search", hours_ago=100)  # >24h, <7d
    await db.commit()

    # 24h window: only the recent event.
    resp24 = await client.get("/stats", params={"site_id": SITE_ID, "window": "24h"})
    assert resp24.status_code == 200
    assert resp24.json()["verdict_counts"] == {"crawler_search": 1}

    # 7d window: both events.
    resp7d = await client.get("/stats", params={"site_id": SITE_ID, "window": "7d"})
    assert resp7d.status_code == 200
    assert resp7d.json()["verdict_counts"] == {"crawler_search": 2}


@pytest.mark.asyncio
async def test_stats_unknown_window_falls_back_to_24h(client):
    db = await get_db()
    await _seed_event(db, path="/recent", verdict="crawler_search", hours_ago=1)
    await _seed_event(db, path="/old", verdict="crawler_search", hours_ago=100)
    await db.commit()

    resp = await client.get("/stats", params={"site_id": SITE_ID, "window": "bogus"})
    assert resp.status_code == 200
    data = resp.json()
    # Falls back to 24h → excludes the 100h-old event, but echoes the raw window value.
    assert data["window"] == "bogus"
    assert data["verdict_counts"] == {"crawler_search": 1}
