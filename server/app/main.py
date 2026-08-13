import hashlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
