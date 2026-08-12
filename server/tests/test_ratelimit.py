"""Tests for the public-endpoint rate limiter."""

import pytest

from app import ratelimit
from app.config import settings
from app.ratelimit import SlidingWindowLimiter


class TestSlidingWindowLimiter:
    def test_allows_up_to_max_then_blocks(self):
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60)
        assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]

    def test_keys_are_independent(self):
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60)
        assert limiter.allow("a") is True
        assert limiter.allow("b") is True
        assert limiter.allow("a") is False

    def test_reset_clears_state(self):
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60)
        assert limiter.allow("a") is True
        limiter.reset()
        assert limiter.allow("a") is True


@pytest.fixture
def prod_limits():
    """Activate rate limiting (demo off) with a clean limiter, then restore."""
    prev = settings.demo_mode
    settings.demo_mode = False
    ratelimit._leads_limiter.reset()
    yield
    settings.demo_mode = prev
    ratelimit._leads_limiter.reset()


@pytest.mark.asyncio
async def test_leads_rate_limited_in_prod(client, prod_limits):
    payload = {"email": "m@store.com", "url": "https://store.com"}
    # Limiter budget is 5/min. Sixth request from the same client → 429.
    statuses = [(await client.post("/leads", json=payload)).status_code for _ in range(6)]
    assert statuses[:5] == [201, 201, 201, 201, 201]
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_leads_not_rate_limited_in_demo(client):
    # client fixture runs in demo mode → limiter is bypassed entirely.
    payload = {"email": "m@store.com", "url": "https://store.com"}
    statuses = [(await client.post("/leads", json=payload)).status_code for _ in range(8)]
    assert all(s == 201 for s in statuses)
