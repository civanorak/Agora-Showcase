"""Tests for the category benchmark API (/stats/benchmark).

The benchmark makes the adoption gap *visible and comparative*: a merchant sees
where they rank against category peers on agent-readability, not just their own
numbers. Competitor identities are anonymized (privacy by default, P5); only the
caller's own row is labeled.
"""

import pytest

from app.db import get_db


async def _add_site(db, site_id: str, name: str, category: str | None) -> None:
    await db.execute(
        "INSERT INTO sites (id, name, api_key_hash, category) VALUES (?, ?, ?, ?)",
        (site_id, name, f"hash-{site_id}", category),
    )


async def _seed_agent_hit(db, site_id: str, status: int) -> None:
    cursor = await db.execute(
        "INSERT INTO events (site_id, method, path, status) VALUES (?, 'GET', '/p', ?)",
        (site_id, status),
    )
    await db.execute(
        "INSERT INTO classifications (event_id, verdict, confidence) VALUES (?, 'shopping_agent', 1.0)",
        (cursor.lastrowid,),
    )


@pytest.mark.asyncio
async def test_benchmark_requires_site_id(client):
    resp = await client.get("/stats/benchmark")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_benchmark_uncategorized_site_returns_empty_board(client):
    db = await get_db()
    await _add_site(db, "solo", "Solo Store", None)
    await db.commit()

    resp = await client.get("/stats/benchmark", params={"site_id": "solo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] is None
    assert data["your_rank"] is None
    assert data["leaderboard"] == []


@pytest.mark.asyncio
async def test_benchmark_ranks_by_agent_success_rate(client):
    db = await get_db()
    await _add_site(db, "you", "Your Store", "footwear")
    await _add_site(db, "rival", "Rival Store", "footwear")
    await _add_site(db, "other", "Other Category", "apparel")

    # You: 1 of 2 agent requests answered → 0.5 success.
    await _seed_agent_hit(db, "you", 200)
    await _seed_agent_hit(db, "you", 404)
    # Rival: 2 of 2 answered → 1.0 success, ranks first.
    await _seed_agent_hit(db, "rival", 200)
    await _seed_agent_hit(db, "rival", 200)
    # Other category must not appear.
    await _seed_agent_hit(db, "other", 200)
    await db.commit()

    resp = await client.get("/stats/benchmark", params={"site_id": "you"})
    data = resp.json()
    assert data["category"] == "footwear"
    assert data["total_in_category"] == 2
    assert data["your_rank"] == 2

    board = data["leaderboard"]
    assert len(board) == 2
    assert board[0]["rank"] == 1
    assert board[0]["agent_success_rate"] == 1.0
    assert board[0]["is_you"] is False
    # Rival identity is anonymized.
    assert board[0]["label"] != "Rival Store"

    you_row = next(r for r in board if r["is_you"])
    assert you_row["rank"] == 2
    assert you_row["agent_success_rate"] == 0.5
    assert you_row["label"] == "Your Store"


@pytest.mark.asyncio
async def test_benchmark_includes_peer_with_zero_agent_traffic(client):
    db = await get_db()
    await _add_site(db, "you", "Your Store", "footwear")
    await _add_site(db, "quiet", "Quiet Peer", "footwear")
    await _seed_agent_hit(db, "you", 200)
    await db.commit()

    resp = await client.get("/stats/benchmark", params={"site_id": "you"})
    data = resp.json()
    assert data["total_in_category"] == 2
    quiet = next(r for r in data["leaderboard"] if not r["is_you"])
    assert quiet["agent_hits"] == 0
    assert quiet["agent_success_rate"] == 0.0
