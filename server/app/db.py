import aiosqlite

from .config import settings

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.sqlite_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def init_db() -> None:
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS sites (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            api_key_hash TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id     TEXT NOT NULL,
            ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            method      TEXT NOT NULL,
            path        TEXT NOT NULL,
            status      INTEGER NOT NULL,
            ua          TEXT NOT NULL DEFAULT '',
            ip_hash     TEXT,
            headers     TEXT DEFAULT '{}',
            beacon_seen INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_events_site_ts ON events (site_id, ts DESC);

        CREATE TABLE IF NOT EXISTS classifications (
            event_id        INTEGER PRIMARY KEY REFERENCES events(id),
            verdict         TEXT NOT NULL,
            confidence      REAL NOT NULL,
            evidence        TEXT NOT NULL DEFAULT '[]',
            signature_id    TEXT,
            sig_version     TEXT NOT NULL DEFAULT 'v1',
            classified_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE TABLE IF NOT EXISTS leads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT NOT NULL,
            url           TEXT,
            coverage_pct  REAL,
            created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads (created_at DESC);
    """)
    # Additive migrations for existing databases (SQLite has no
    # ADD COLUMN IF NOT EXISTS, so we probe the schema first).
    await _ensure_column(db, "sites", "category", "category TEXT")
    await db.commit()


async def _ensure_column(
    db: aiosqlite.Connection, table: str, column: str, ddl: str
) -> None:
    """Add a column if it is missing, so restarts on an older DB self-migrate."""
    cursor = await db.execute(f"PRAGMA table_info({table})")
    existing = {row["name"] for row in await cursor.fetchall()}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
