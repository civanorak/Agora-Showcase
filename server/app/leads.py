import re

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, field_validator

from .ratelimit import limit_leads

from .auth import require_admin
from .db import get_db

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadCapture(BaseModel):
    # This endpoint is public (the free audit captures merchant emails), so every
    # field is bounded to keep an unauthenticated caller from writing oversized
    # rows into the leads table.
    email: str = Field(max_length=254)  # RFC 5321 max email length
    url: str = Field(max_length=2048)
    coverage_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class LeadCaptured(BaseModel):
    status: str = "ok"


class LeadSummary(BaseModel):
    id: int
    email: str
    url: str | None
    coverage_pct: float | None
    created_at: str


@router.post(
    "/leads",
    response_model=LeadCaptured,
    status_code=201,
    dependencies=[Depends(limit_leads)],
)
async def capture_lead(body: LeadCapture) -> LeadCaptured:
    db = await get_db()
    await db.execute(
        "INSERT INTO leads (email, url, coverage_pct) VALUES (?, ?, ?)",
        (body.email, body.url, body.coverage_pct),
    )
    await db.commit()
    return LeadCaptured()


@router.get("/leads", response_model=list[LeadSummary])
async def list_leads(authorization: str = Header(default="")) -> list[LeadSummary]:
    require_admin(authorization)
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, email, url, coverage_pct, created_at
        FROM leads
        ORDER BY (coverage_pct IS NULL), coverage_pct ASC, created_at DESC
        """
    )
    rows = await cursor.fetchall()
    return [
        LeadSummary(
            id=r["id"],
            email=r["email"],
            url=r["url"],
            coverage_pct=r["coverage_pct"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
