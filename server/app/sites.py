import hashlib
import secrets

from fastapi import APIRouter, Header
from pydantic import BaseModel

from .auth import require_admin
from .db import get_db

router = APIRouter()


class SiteCreate(BaseModel):
    name: str
    # Category groups competing stores for the agent-readiness benchmark
    # (/stats/benchmark). Optional — an ungrouped site simply gets no peers.
    category: str | None = None


class SiteCreated(BaseModel):
    id: str
    name: str
    api_key: str
    category: str | None = None


class SiteSummary(BaseModel):
    id: str
    name: str
    event_count: int
    category: str | None = None


@router.post("/sites", response_model=SiteCreated, status_code=201)
async def create_site(
    body: SiteCreate,
    authorization: str = Header(default=""),
):
    require_admin(authorization)
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    site_id = secrets.token_hex(8)
    db = await get_db()
    await db.execute(
        "INSERT INTO sites (id, name, api_key_hash, category) VALUES (?, ?, ?, ?)",
        (site_id, body.name, key_hash, body.category),
    )
    await db.commit()
    return SiteCreated(id=site_id, name=body.name, api_key=raw_key, category=body.category)


@router.get("/sites", response_model=list[SiteSummary])
async def list_sites(authorization: str = Header(default="")):
    require_admin(authorization)
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT s.id, s.name, s.category, COUNT(e.id) AS event_count
        FROM sites s
        LEFT JOIN events e ON e.site_id = s.id
        GROUP BY s.id, s.name, s.category
        ORDER BY s.name
        """
    )
    rows = await cursor.fetchall()
    return [
        SiteSummary(
            id=r["id"], name=r["name"], event_count=r["event_count"], category=r["category"]
        )
        for r in rows
    ]
