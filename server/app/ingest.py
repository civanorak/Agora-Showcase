import asyncio
import hashlib
import json
import logging
import random

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel

from .auth import require_read_access
from .classifier import classify
from .config import settings
from .db import get_db
from .models import EventIn

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory SSE pub/sub — keyed on client Queue, no SQLite polling on the hot path.
_subscribers: set[asyncio.Queue] = set()


async def _publish(payload: dict) -> None:
    dead: set[asyncio.Queue] = set()
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.add(q)
    _subscribers.difference_update(dead)


class IngestResponse(BaseModel):
    ok: bool
    event_id: int | None = None
    verdict: str | None = None
    confidence: float | None = None


class EventOut(BaseModel):
    id: int
    ts: str
    method: str
    path: str
    status: int
    ua: str
    verdict: str | None = None
    confidence: float | None = None
    evidence: list[str] = []


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{settings.api_key_hash_salt}:{ip}".encode()).hexdigest()[:16]


def _extract_ip(xff: str | None, xri: str | None) -> str:
    if xff:
        return xff.split(",")[0].strip()
    if xri:
        return xri.strip()
    return "127.0.0.1"


async def _validate_key(raw_key: str, db) -> str | None:
    """Return site_id if key is valid, None otherwise."""
    # demo-key bypass only active when AGORA_DEMO_MODE=1 (D-INT-4).
    # demo-site is auto-registered in DB at startup when demo_mode is on (M3).
    if settings.demo_mode and raw_key == "demo-key":
        return "demo-site"
    key_hash = _hash_key(raw_key)
    cursor = await db.execute("SELECT id FROM sites WHERE api_key_hash = ?", (key_hash,))
    row = await cursor.fetchone()
    return row["id"] if row else None


@router.post("/ingest", response_model=IngestResponse)
async def ingest_event(
    event: EventIn,
    authorization: str = Header(default=""),
    x_forwarded_for: str | None = Header(default=None),
    x_real_ip: str | None = Header(default=None),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    raw_key = authorization.removeprefix("Bearer ").strip()
    db = await get_db()

    site_id = await _validate_key(raw_key, db)
    if site_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    client_ip = _extract_ip(x_forwarded_for, x_real_ip)
    result = classify(ua=event.ua, path=event.path, headers=dict(event.headers))

    try:
        cursor = await db.execute(
            """
            INSERT INTO events (site_id, ts, method, path, status, ua, ip_hash, headers, beacon_seen)
            VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site_id,
                event.method,
                event.path,
                event.status,
                event.ua,
                _hash_ip(client_ip),
                json.dumps(event.headers),
                1 if event.beacon_seen else 0,
            ),
        )
        event_id = cursor.lastrowid

        await db.execute(
            """
            INSERT INTO classifications (event_id, verdict, confidence, evidence, signature_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                result.verdict,
                result.confidence,
                json.dumps(result.evidence),
                result.signature_id,
            ),
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to insert event")
        raise HTTPException(status_code=500, detail="Ingest failed")

    ts_cursor = await db.execute("SELECT ts FROM events WHERE id = ?", (event_id,))
    ts_row = await ts_cursor.fetchone()
    ts = ts_row["ts"] if ts_row else ""

    await _publish(
        {
            "id": event_id,
            "ts": ts,
            "method": event.method,
            "path": event.path,
            "status": event.status,
            "ua": event.ua,
            "verdict": result.verdict,
            "confidence": result.confidence,
            "evidence": result.evidence,
        }
    )

    return IngestResponse(
        ok=True,
        event_id=event_id,
        verdict=result.verdict,
        confidence=result.confidence,
    )


@router.get("/events/stream")
async def stream_events(authorization: str = Header(default="")):
    """SSE stream — pushes each new event as it is ingested. 15 s heartbeat."""
    require_read_access(authorization)
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)

    async def generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            _subscribers.discard(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/events", response_model=list[EventOut])
async def list_events(limit: int = 50, authorization: str = Header(default="")):
    require_read_access(authorization)
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT e.id, e.ts, e.method, e.path, e.status, e.ua,
               c.verdict, c.confidence, c.evidence
        FROM events e
        LEFT JOIN classifications c ON c.event_id = e.id
        ORDER BY e.id DESC LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        EventOut(
            id=r["id"],
            ts=r["ts"],
            method=r["method"],
            path=r["path"],
            status=r["status"],
            ua=r["ua"],
            verdict=r["verdict"],
            confidence=r["confidence"],
            evidence=json.loads(r["evidence"]) if r["evidence"] else [],
        )
        for r in rows
    ]


LLMS_TXT_CONTENT = """# AGORA Demo Store

This is the LLM-friendly storefront description.

## Profile
- Name: AGORA Demo Store
- Description: AI-agent optimized analytics demo storefront selling high-quality electronics and accessories.

## Products
- Wireless Headphones Pro: Premium wireless over-ear headphones with active noise cancelling. Price: $299.
- Leather Wallet Slim: Genuine minimalist leather wallet with RFID protection. Price: $49.
- Mechanical Keyboard TKL: Tactile brown switch mechanical keyboard with RGB backlighting. Price: $129.
"""


@router.get("/llms.txt", response_class=PlainTextResponse)
async def serve_llms_txt(
    user_agent: str | None = Header(default="", alias="User-Agent"),
    x_forwarded_for: str | None = Header(default=None),
    x_real_ip: str | None = Header(default=None),
    accept: str | None = Header(default=None),
    accept_language: str | None = Header(default=None),
):
    """Serve LLM instructions file. Ingests event if AGORA_DEMO_MODE=1."""
    if settings.demo_mode:
        db = await get_db()
        client_ip = _extract_ip(x_forwarded_for, x_real_ip)

        headers_dict = {}
        if accept:
            headers_dict["accept"] = accept
        if accept_language:
            headers_dict["accept-language"] = accept_language
        if user_agent:
            headers_dict["user-agent"] = user_agent

        result = classify(ua=user_agent or "", path="/llms.txt", headers=headers_dict)

        try:
            cursor = await db.execute(
                """
                INSERT INTO events (site_id, ts, method, path, status, ua, ip_hash, headers, beacon_seen)
                VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "demo-site",
                    "GET",
                    "/llms.txt",
                    200,
                    user_agent or "",
                    _hash_ip(client_ip),
                    json.dumps(headers_dict),
                    0,
                ),
            )
            event_id = cursor.lastrowid

            await db.execute(
                """
                INSERT INTO classifications (event_id, verdict, confidence, evidence, signature_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    result.verdict,
                    result.confidence,
                    json.dumps(result.evidence),
                    result.signature_id,
                ),
            )
            await db.commit()

            ts_cursor = await db.execute("SELECT ts FROM events WHERE id = ?", (event_id,))
            ts_row = await ts_cursor.fetchone()
            ts = ts_row["ts"] if ts_row else ""

            await _publish(
                {
                    "id": event_id,
                    "ts": ts,
                    "method": "GET",
                    "path": "/llms.txt",
                    "status": 200,
                    "ua": user_agent or "",
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                    "evidence": result.evidence,
                }
            )
        except Exception:
            logger.exception("Failed to insert /llms.txt event in demo mode")
            # Fail-open per P7

    return PlainTextResponse(content=LLMS_TXT_CONTENT, media_type="text/plain")


@router.post("/events/simulate")
async def simulate_bot_visit(agent: str = Query(...)):
    """Simulate a bot visit directly from the dashboard (only in demo mode)."""
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")

    agent_profiles = {
        "chatgpt": {
            "ua": "ChatGPT-User/1.0 (+https://openai.com/bot)",
            "path": "/llms.txt",
            "method": "GET",
            "status": 200,
        },
        "claude": {
            "ua": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +http://www.anthropic.com/claudebot)",
            "path": "/products",
            "method": "GET",
            "status": 200,
        },
        "perplexity": {
            "ua": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +http://www.perplexity.ai/bot.html)",
            "path": "/llms.txt",
            "method": "GET",
            "status": 200,
        },
    }

    profile = agent_profiles.get(agent.lower())
    if not profile:
        raise HTTPException(status_code=400, detail="Invalid agent profile")

    db = await get_db()
    client_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    headers_dict = {
        "host": "agora-demo-store.com",
        "user-agent": profile["ua"],
        "accept": "text/html",
    }

    result = classify(ua=profile["ua"], path=profile["path"], headers=headers_dict)

    try:
        cursor = await db.execute(
            """
            INSERT INTO events (site_id, ts, method, path, status, ua, ip_hash, headers, beacon_seen)
            VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo-site",
                profile["method"],
                profile["path"],
                profile["status"],
                profile["ua"],
                _hash_ip(client_ip),
                json.dumps(headers_dict),
                0,
            ),
        )
        event_id = cursor.lastrowid

        await db.execute(
            """
            INSERT INTO classifications (event_id, verdict, confidence, evidence, signature_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                result.verdict,
                result.confidence,
                json.dumps(result.evidence),
                result.signature_id,
            ),
        )
        await db.commit()

        ts_cursor = await db.execute("SELECT ts FROM events WHERE id = ?", (event_id,))
        ts_row = await ts_cursor.fetchone()
        ts = ts_row["ts"] if ts_row else ""

        await _publish(
            {
                "id": event_id,
                "ts": ts,
                "method": profile["method"],
                "path": profile["path"],
                "status": profile["status"],
                "ua": profile["ua"],
                "verdict": result.verdict,
                "confidence": result.confidence,
                "evidence": result.evidence,
            }
        )
    except Exception:
        logger.exception("Failed to simulate agent visit")
        raise HTTPException(status_code=500, detail="Simulation failed")

    return {"ok": True, "event_id": event_id, "verdict": result.verdict}
