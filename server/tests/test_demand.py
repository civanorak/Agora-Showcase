"""Tests for the agent demand-signal API (/stats/demand).

Demand signal is the intelligence only an AGORA adopter gets: which products
agents are actually asking about, and whether the store could answer (2xx) or
turned them away (4xx/5xx). It is derived purely from measured events and their
classifications — no estimation.
"""

import pytest

from app.db import get_db

SITE_ID = "demand-site"


async def _seed(db, *, path: str, verdict: str, status: int = 200, hours_ago: int = 1) -> None:
    cursor = await db.execute(
        """
        INSERT INTO events (site_id, ts, method, path, status)
        VALUES (?, datetime('now', ?), 'GET', ?, ?)
        """,
        (SITE_ID, f"-{hours_ago} hours", path, status),
    )
    event_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO classifications (event_id, verdict, confidence) VALUES (?, ?, 1.0)",
        (event_id, verdict),
    )


@pytest.mark.asyncio
async def test_demand_requires_site_id(client):
    resp = await client.get("/stats/demand")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_demand_empty_site_returns_zeroed_shape(client):
    resp = await client.get("/stats/demand", params={"site_id": SITE_ID})
    assert resp.status_code == 200
    data = resp.json()
    assert data["site_id"] == SITE_ID
    assert data["window"] == "24h"
    assert data["total_agent_hits"] == 0
    assert data["top_products"] == []


@pytest.mark.asyncio
async def test_demand_ranks_agent_requested_paths(client):
    db = await get_db()
    # Two agents ask about /products/shoe, one about /products/hat.
    await _seed(db, path="/products/shoe", verdict="shopping_agent")
    await _seed(db, path="/products/shoe", verdict="assistant_browse")
    await _seed(db, path="/products/hat", verdict="crawler_search")
    await db.commit()

    resp = await client.get("/stats/demand", params={"site_id": SITE_ID})
    data = resp.json()
    assert data["total_agent_hits"] == 3
    top = data["top_products"]
    assert top[0]["path"] == "/products/shoe"
    assert top[0]["agent_hits"] == 2
    assert top[0]["verdicts"] == {"shopping_agent": 1, "assistant_browse": 1}
    assert top[1]["path"] == "/products/hat"


@pytest.mark.asyncio
async def test_demand_excludes_human_and_training_traffic(client):
    db = await get_db()
    await _seed(db, path="/products/shoe", verdict="shopping_agent")
    await _seed(db, path="/products/shoe", verdict="human")
    await _seed(db, path="/products/shoe", verdict="crawler_training")
    await db.commit()

    resp = await client.get("/stats/demand", params={"site_id": SITE_ID})
    data = resp.json()
    # Only the shopping_agent hit is demand; human + training excluded.
    assert data["total_agent_hits"] == 1
    assert data["top_products"][0]["agent_hits"] == 1


@pytest.mark.asyncio
async def test_demand_reports_success_rate(client):
    db = await get_db()
    # Agent asked 4 times, store answered 3, 404'd once → 0.75 success.
    await _seed(db, path="/products/shoe", verdict="shopping_agent", status=200)
    await _seed(db, path="/products/shoe", verdict="shopping_agent", status=200)
    await _seed(db, path="/products/shoe", verdict="shopping_agent", status=200)
    await _seed(db, path="/products/shoe", verdict="shopping_agent", status=404)
    await db.commit()

    resp = await client.get("/stats/demand", params={"site_id": SITE_ID})
    row = resp.json()["top_products"][0]
    assert row["agent_hits"] == 4
    assert row["success_rate"] == 0.75


@pytest.mark.asyncio
async def test_demand_window_excludes_older_events(client):
    db = await get_db()
    await _seed(db, path="/recent", verdict="shopping_agent", hours_ago=1)
    await _seed(db, path="/old", verdict="shopping_agent", hours_ago=100)
    await db.commit()

    resp = await client.get("/stats/demand", params={"site_id": SITE_ID, "window": "24h"})
    assert resp.json()["total_agent_hits"] == 1
