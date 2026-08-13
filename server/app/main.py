import hashlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings, verify_production_secrets
from .crawler import router as crawler_router
from .db import close_db, get_db, init_db
from .ingest import router as ingest_router
from .leads import router as leads_router
from .report import router as report_router
from .sites import router as sites_router
from .stats import router as stats_router


async def _ensure_demo_site() -> None:
    """Register demo-site in DB when AGORA_DEMO_MODE=1 (M3).
    Uses INSERT OR IGNORE so repeated starts are safe."""
    db = await get_db()
    key_hash = hashlib.sha256(b"demo-key").hexdigest()
    await db.execute(
        "INSERT OR IGNORE INTO sites (id, name, api_key_hash) VALUES (?, ?, ?)",
        ("demo-site", "Demo Store", key_hash),
    )
    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_production_secrets(settings)
    await init_db()
    if settings.demo_mode:
        await _ensure_demo_site()
    yield
    await close_db()


app = FastAPI(title="AGORA", version="0.1.0", lifespan=lifespan)

origins = ["*"] if settings.demo_mode else settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(stats_router)
app.include_router(sites_router)
app.include_router(report_router)
app.include_router(crawler_router)
app.include_router(leads_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ── Static SPA Fallback Handler ──────────────────────────────────────────────
_dist_dir = Path(__file__).resolve().parent.parent.parent / "dashboard" / "dist"
if not _dist_dir.exists():
    for alt in [
        Path.cwd() / "dashboard" / "dist",
        Path("/var/task/dashboard/dist"),
        Path(__file__).resolve().parent.parent / "dist",
    ]:
        if alt.exists():
            _dist_dir = alt
            break

if _dist_dir.exists() and (_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")


def _get_index_html() -> str:
    index_file = _dist_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AGORA — AI Traffic Dashboard</title>
  <style>body{font-family:sans-serif;background:#09090b;color:#fff;display:grid;place-content:center;height:100vh;margin:0;}h1{font-size:2rem;}</style>
</head>
<body>
  <div>
    <h1>AGORA — AI Traffic Engine</h1>
    <p>Backend API is active and ready.</p>
  </div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=_get_index_html())


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all_spa(full_path: str = ""):
    # Do not intercept API endpoints
    if any(full_path.startswith(prefix) for prefix in ["api/", "health", "report", "events", "stats", "sites", "leads", "ingest"]):
        return HTMLResponse(content='{"detail":"Not Found"}', status_code=404)

    if full_path and _dist_dir.exists():
        target_file = _dist_dir / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)

    return HTMLResponse(content=_get_index_html())
