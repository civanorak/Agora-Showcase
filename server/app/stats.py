from fastapi import APIRouter, Header, Query

from .auth import require_read_access
from .db import get_db

router = APIRouter()

_WINDOW_HOURS = {"24h": 24, "7d": 168}

# Discovery-oriented agent verdicts: an agent looking for / browsing / buying a
# product. Training scrapers (crawler_training), humans, and generic automation
# are excluded — they are not purchase-intent demand.
_AGENT_VERDICTS = ("shopping_agent", "assistant_browse", "crawler_search")
_AGENT_VERDICTS_SQL = ",".join("?" for _ in _AGENT_VERDICTS)
_DEMAND_LIMIT = 20


@router.get("/stats")
async def get_stats(
    site_id: str = Query(...),
    window: str = Query("24h"),
    authorization: str = Header(default=""),
):
    require_read_access(authorization)
    hours = _WINDOW_HOURS.get(window, 24)
    interval = f"-{hours} hours"
    db = await get_db()

    verdict_cursor = await db.execute(
        """
        SELECT c.verdict, COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ?
          AND e.ts >= datetime('now', ?)
        GROUP BY c.verdict
        """,
        (site_id, interval),
    )
    verdict_rows = await verdict_cursor.fetchall()
    verdict_counts = {r["verdict"]: r["count"] for r in verdict_rows}

    path_cursor = await db.execute(
        """
        SELECT e.path, COUNT(*) AS count
        FROM events e
        WHERE e.site_id = ?
          AND e.ts >= datetime('now', ?)
        GROUP BY e.path
        ORDER BY count DESC
        LIMIT 10
        """,
        (site_id, interval),
    )
    path_rows = await path_cursor.fetchall()
    top_paths = [{"path": r["path"], "count": r["count"]} for r in path_rows]

    bucket_cursor = await db.execute(
        """
        SELECT strftime('%Y-%m-%dT%H:00:00Z', e.ts) AS hour,
               c.verdict,
               COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ?
          AND e.ts >= datetime('now', ?)
        GROUP BY hour, c.verdict
        ORDER BY hour
        """,
        (site_id, interval),
    )
    bucket_rows = await bucket_cursor.fetchall()
    hourly_buckets = [
        {"hour": r["hour"], "verdict": r["verdict"], "count": r["count"]} for r in bucket_rows
    ]

    return {
        "site_id": site_id,
        "window": window,
        "verdict_counts": verdict_counts,
        "top_paths": top_paths,
        "hourly_buckets": hourly_buckets,
    }


@router.get("/stats/demand")
async def get_demand(
    site_id: str = Query(...),
    window: str = Query("24h"),
    authorization: str = Header(default=""),
):
    """Which products agents are asking about — the intelligence only an adopter
    sees. Ranks paths hit by discovery-oriented agents, with the store's answer
    rate (2xx) per path so a merchant can spot demand it is failing to serve.
    All values are measured from events; none are estimated."""
    require_read_access(authorization)
    hours = _WINDOW_HOURS.get(window, 24)
    interval = f"-{hours} hours"
    db = await get_db()

    path_cursor = await db.execute(
        f"""
        SELECT e.path,
               COUNT(*) AS agent_hits,
               SUM(CASE WHEN e.status < 400 THEN 1 ELSE 0 END) AS ok_hits,
               MAX(e.ts) AS last_seen
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ?
          AND e.ts >= datetime('now', ?)
          AND c.verdict IN ({_AGENT_VERDICTS_SQL})
        GROUP BY e.path
        ORDER BY agent_hits DESC, last_seen DESC
        LIMIT ?
        """,
        (site_id, interval, *_AGENT_VERDICTS, _DEMAND_LIMIT),
    )
    path_rows = await path_cursor.fetchall()

    breakdown_cursor = await db.execute(
        f"""
        SELECT e.path, c.verdict, COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ?
          AND e.ts >= datetime('now', ?)
          AND c.verdict IN ({_AGENT_VERDICTS_SQL})
        GROUP BY e.path, c.verdict
        """,
        (site_id, interval, *_AGENT_VERDICTS),
    )
    verdicts_by_path: dict[str, dict[str, int]] = {}
    for r in await breakdown_cursor.fetchall():
        verdicts_by_path.setdefault(r["path"], {})[r["verdict"]] = r["count"]

    top_products = []
    total_agent_hits = 0
    for r in path_rows:
        hits = r["agent_hits"]
        total_agent_hits += hits
        top_products.append(
            {
                "path": r["path"],
                "agent_hits": hits,
                "success_rate": round(r["ok_hits"] / hits, 4) if hits else 0.0,
                "last_seen": r["last_seen"],
                "verdicts": verdicts_by_path.get(r["path"], {}),
            }
        )

    return {
        "site_id": site_id,
        "window": window,
        "agent_verdicts": list(_AGENT_VERDICTS),
        "total_agent_hits": total_agent_hits,
        "top_products": top_products,
    }


@router.get("/stats/benchmark")
async def get_benchmark(
    site_id: str = Query(...),
    window: str = Query("24h"),
    authorization: str = Header(default=""),
):
    """Rank a store against its category peers on agent-readability. Score is the
    agent success rate (share of agent requests answered with 2xx); ties break on
    agent volume. Peer identities are anonymized — only the caller's own row is
    labeled — so the scoreboard motivates without leaking a competitor's traffic."""
    require_read_access(authorization)
    hours = _WINDOW_HOURS.get(window, 24)
    interval = f"-{hours} hours"
    db = await get_db()

    empty = {
        "site_id": site_id,
        "window": window,
        "category": None,
        "your_rank": None,
        "total_in_category": 0,
        "leaderboard": [],
    }

    cat_cursor = await db.execute("SELECT category FROM sites WHERE id = ?", (site_id,))
    cat_row = await cat_cursor.fetchone()
    if cat_row is None or cat_row["category"] is None:
        return empty
    category = cat_row["category"]

    # Conditional aggregation keeps peers with zero agent traffic in the board
    # (a quiet store still occupies a rank), which an INNER JOIN would drop.
    rows_cursor = await db.execute(
        f"""
        SELECT s.id, s.name,
               SUM(CASE WHEN c.verdict IN ({_AGENT_VERDICTS_SQL}) THEN 1 ELSE 0 END) AS agent_hits,
               SUM(CASE WHEN c.verdict IN ({_AGENT_VERDICTS_SQL}) AND e.status < 400
                        THEN 1 ELSE 0 END) AS ok_hits
        FROM sites s
        LEFT JOIN events e ON e.site_id = s.id AND e.ts >= datetime('now', ?)
        LEFT JOIN classifications c ON c.event_id = e.id
        WHERE s.category = ?
        GROUP BY s.id, s.name
        """,
        (*_AGENT_VERDICTS, *_AGENT_VERDICTS, interval, category),
    )
    rows = await rows_cursor.fetchall()

    scored = []
    for r in rows:
        hits = r["agent_hits"] or 0
        ok = r["ok_hits"] or 0
        success_rate = round(ok / hits, 4) if hits else 0.0
        scored.append(
            {
                "id": r["id"],
                "name": r["name"],
                "agent_hits": hits,
                "agent_success_rate": success_rate,
            }
        )
    # Best readability first; ties broken by who serves more agent traffic.
    scored.sort(key=lambda s: (-s["agent_success_rate"], -s["agent_hits"]))

    leaderboard = []
    your_rank = None
    for idx, s in enumerate(scored, start=1):
        is_you = s["id"] == site_id
        if is_you:
            your_rank = idx
        leaderboard.append(
            {
                "rank": idx,
                "is_you": is_you,
                "label": s["name"] if is_you else f"Competitor #{idx}",
                "agent_hits": s["agent_hits"],
                "agent_success_rate": s["agent_success_rate"],
                "score": round(s["agent_success_rate"] * 100, 1),
            }
        )

    return {
        "site_id": site_id,
        "window": window,
        "category": category,
        "your_rank": your_rank,
        "total_in_category": len(scored),
        "leaderboard": leaderboard,
    }
