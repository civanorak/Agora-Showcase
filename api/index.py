"""Vercel Serverless Function entry point for AGORA.

Vercel's Python runtime invokes this as an ASGI handler.
Requests arrive at /api/* — we strip the /api prefix so FastAPI's
routes (/health, /report/analyze, etc.) match correctly.
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
    from fastapi import FastAPI
    _fastapi_app = FastAPI()
    _import_error = "".join(traceback.format_exception(exc))

    @_fastapi_app.get("/{path:path}")
    async def _diag(path: str = ""):
        return {"error": "App import failed", "detail": _import_error}


# ── 4. Lazy cold-start init ─────────────────────────────────────────────
# Vercel doesn't fire ASGI lifespan events, so we init on first request.
import hashlib
_serverless_ready = False


async def _ensure_serverless_ready():
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


# ── 5. ASGI wrapper: strip /api prefix + cold-start init ───────────────
from starlette.types import ASGIApp, Receive, Scope, Send


class _VercelASGIWrapper:
    """Strips /api or /api/index prefix so FastAPI routes match,
    and runs one-time cold-start initialization on first request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            await _ensure_serverless_ready()
            path: str = scope.get("path", "")
            if path.startswith("/api/index"):
                scope["path"] = path[len("/api/index"):] or "/"
            elif path.startswith("/api"):
                scope["path"] = path[4:] or "/"
        await self.app(scope, receive, send)


# ── 6. Export ───────────────────────────────────────────────────────────
app = _VercelASGIWrapper(_fastapi_app)
