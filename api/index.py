"""Vercel Serverless Function entry point for AGORA.

Vercel's Python runtime invokes this as an ASGI handler.
Requests arrive at /api/* — we strip the /api prefix so FastAPI's
routes (/health, /report/analyze, etc.) match correctly.
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

# ── 1. Environment setup (MUST happen before any app import) ────────────
# Force-set all config values for Vercel serverless.
# Vercel auto-imports .env.example values which break pydantic_settings parsing
# (especially AGORA_CORS_ORIGINS with embedded JSON quotes).
_tmp_db = os.environ.get("AGORA_SQLITE_PATH") or str(Path(tempfile.gettempdir()) / "agora.db")
os.environ["AGORA_SQLITE_PATH"] = _tmp_db
os.environ["AGORA_DEMO_MODE"] = "1"
os.environ["AGORA_CORS_ORIGINS"] = '["*"]'
os.environ["AGORA_LOG_LEVEL"] = "INFO"
os.environ["AGORA_API_KEY_HASH_SALT"] = "vercel-showcase-demo-salt-not-for-production"
os.environ["AGORA_ADMIN_TOKEN"] = ""
os.environ["AGORA_DATABASE_URL"] = f"sqlite:///{_tmp_db}"

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


from starlette.types import ASGIApp, Receive, Scope, Send
from urllib.parse import parse_qs, urlencode


class _VercelASGIWrapper:
    """Strips /api, /api/index, or /api/index.py prefix so FastAPI routes match,
    and runs one-time cold-start initialization on first request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            await _ensure_serverless_ready()
            path: str = scope.get("path", "")

            # 1. Check query parameter __path from vercel.json rewrite
            query_raw = scope.get("query_string", b"").decode("latin1", "replace")
            if "__path=" in query_raw:
                qs = parse_qs(query_raw)
                if "__path" in qs and qs["__path"]:
                    extracted = qs["__path"][0]
                    if extracted:
                        path = extracted
                    clean_qs = {k: v for k, v in qs.items() if k != "__path"}
                    scope["query_string"] = urlencode(clean_qs, doseq=True).encode("latin1")

            # 2. If path is generic /api/index.py, inspect headers
            if path in ("/api/index.py", "/api/index", "/api", "", "/"):
                headers_dict = {}
                for k, v in scope.get("headers", []):
                    try:
                        headers_dict[k.decode("latin1").lower()] = v.decode("latin1")
                    except Exception:
                        pass
                matched = (
                    headers_dict.get("x-matched-path")
                    or headers_dict.get("x-vercel-matched-path")
                    or headers_dict.get("x-forwarded-uri")
                )
                if matched:
                    path = matched

            # 3. Strip serverless /api prefixes
            for prefix in ("/api/index.py", "/api/index", "/api"):
                if path.startswith(prefix):
                    path = path[len(prefix):]
                    break

            if not path.startswith("/"):
                path = "/" + path

            scope["path"] = path

        await self.app(scope, receive, send)


# ── 6. Export ───────────────────────────────────────────────────────────
app = _VercelASGIWrapper(_fastapi_app)
