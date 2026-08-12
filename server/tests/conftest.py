import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db import init_db, get_db, close_db


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Ensure database tables exist and are cleared before each test runs."""
    await init_db()
    db = await get_db()
    await db.execute("DELETE FROM classifications")
    await db.execute("DELETE FROM events")
    await db.execute("DELETE FROM sites")
    await db.execute("DELETE FROM leads")
    await db.commit()
    yield
    # aiosqlite runs on a non-daemon thread; leaving the global connection
    # open keeps the pytest process alive forever after the suite passes.
    await close_db()


@pytest.fixture
async def client():
    from app.config import settings

    settings.demo_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    settings.demo_mode = False
