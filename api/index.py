"""Vercel Serverless Function entry point for AGORA.

Vercel's Python runtime invokes this as an ASGI handler.
Key adaptations for serverless:
- Environment variables set BEFORE any app import
- uvicorn is NOT used (Vercel has its own ASGI adapter)
- Lifespan events may not fire, so we use middleware for lazy init
"""
import os
import sys
import traceback
from pathlib import Path

# ── 1. Environment setup (MUST happen before any app import) ────────────
if "AGORA_SQLITE_PATH" not in os.environ:
    os.environ["AGORA_SQLITE_PATH"] = "/tmp/agora.db"

if "AGORA_DEMO_MODE" not in os.environ:
    os.environ["AGORA_DEMO_MODE"] = "1"

# ── 2. Fix Python path so `from app.xxx import ...` resolves ────────────
_root = Path(__file__).resolve().parent.parent
_server_dir = _root / "server"
if str(_server_dir) not in sys.path:
    sys.path.insert(0, str(_server_dir))

# ── 3. Import the real app, with full error diagnostics ─────────────────
try:
    from app.main import app as _fastapi_app  # noqa: E402
except Exception as exc:
    # If the import fails, create a diagnostic app so Vercel shows the
    # actual error instead of a generic 500.
    from fastapi import FastAPI
    _fastapi_app = FastAPI()
    _import_error = "".join(traceback.format_exception(exc))

    @_fastapi_app.get("/{path:path}")
    async def _diag(path: str = ""):
        return {"error": "App import failed", "detail": _import_error}


# ── 4. Lazy-init wrapper ────────────────────────────────────────────────
# Vercel may not fire ASGI lifespan events, so we initialise the DB and
# demo-site on the FIRST actual HTTP request via startup middleware.

import hashlib
_serverless_ready = False


async def _ensure_serverless_ready():
    """One-time cold-start initialisation (runs inside the first request)."""
    global _serverless_ready
    if _serverless_ready:
        return
    _serverless_ready = True

    from app.db import init_db, get_db
    from app.config import settings
    from app.classifier import load_signatures

    await init_db()
    load_signatures()

    if settings.demo_mode:
        db = await get_db()
        key_hash = hashlib.sha256(b"demo-key").hexdigest()
        await db.execute(
            "INSERT OR IGNORE INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
            ("demo-site", "Demo Store", key_hash),
        )
        await db.commit()


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class _ColdStartMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        await _ensure_serverless_ready()
        return await call_next(request)


_fastapi_app.add_middleware(_ColdStartMiddleware)

# ── 5. Export ───────────────────────────────────────────────────────────
app = _fastapi_app
