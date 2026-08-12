import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_UA_MAX_BYTES = 2048
_HEADERS_MAX_BYTES = 8192


class EventIn(BaseModel):
    """Incoming event from collector or direct POST."""

    method: str = Field(..., max_length=10)
    path: str
    status: int = Field(..., ge=100, le=599)
    ua: str = Field(default="", alias="user_agent")
    ip: str = Field(default="")
    headers: dict = Field(default_factory=dict)
    # Informational only — the server derives the real site from the API key.
    # Collectors send their configured string id ("demo-site", token_hex ids).
    site_id: str = Field(default="", max_length=64)
    beacon_seen: bool = False

    model_config = {"populate_by_name": True}

    @field_validator("ua", mode="before")
    @classmethod
    def truncate_ua(cls, v: object) -> str:
        if not isinstance(v, str):
            return ""
        encoded = v.encode("utf-8", errors="ignore")
        if len(encoded) > _UA_MAX_BYTES:
            return encoded[:_UA_MAX_BYTES].decode("utf-8", errors="ignore")
        return v

    @field_validator("headers", mode="before")
    @classmethod
    def cap_headers(cls, v: object) -> dict:
        if not isinstance(v, dict):
            return {}
        if len(json.dumps(v).encode()) <= _HEADERS_MAX_BYTES:
            return v
        # Drop entries until we fit — preserve order, drop tail
        trimmed: dict = {}
        for k, val in v.items():
            candidate = {**trimmed, k: val}
            if len(json.dumps(candidate).encode()) > _HEADERS_MAX_BYTES:
                break
            trimmed = candidate
        return trimmed


class EventDB(BaseModel):
    """Stored event with server-assigned fields."""

    id: int
    site_id: str
    ts: datetime
    method: str
    path: str
    status: int
    ua: str
    ip_hash: str | None = None
    headers: dict = Field(default_factory=dict)
    beacon_seen: bool = False
