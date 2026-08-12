"""Lightweight in-process rate limiting for public, unauthenticated endpoints.

The free audit (`POST /report/analyze`) makes outbound requests on the caller's
behalf and the lead capture (`POST /leads`) writes to the DB — both are reachable
without an API key, so an unthrottled caller can use them to amplify traffic,
scan hosts, or spam the leads table. This module provides a per-client sliding
window with no external dependency (Redis-free; fine for the single-node MVP).

Rate limiting is skipped in demo mode so the local demo and the test suite can
poll freely — the same open-in-demo contract used by the read endpoints.
"""

import time
from collections import deque

from fastapi import Header, HTTPException, Request

from .config import settings


class SlidingWindowLimiter:
    """Allow at most `max_requests` per `window_seconds` per key.

    Uses a monotonic clock so it is immune to wall-clock adjustments. State is
    process-local; a multi-worker deployment should move this to Redis (noted in
    the ADR), but for a single-node MVP this bounds abuse effectively.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


# Budgets are per client IP per minute. Tuned generous enough for real merchant
# use, tight enough to stop scripted abuse.
_audit_limiter = SlidingWindowLimiter(max_requests=10, window_seconds=60)
_leads_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)


def _client_key(request: Request, x_forwarded_for: str | None) -> str:
    """Best-effort client identity: first XFF hop, else the socket peer."""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _enforce(
    limiter: SlidingWindowLimiter, request: Request, x_forwarded_for: str | None
) -> None:
    if settings.demo_mode:
        return
    if not limiter.allow(_client_key(request, x_forwarded_for)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")


async def limit_audit(
    request: Request, x_forwarded_for: str | None = Header(default=None)
) -> None:
    _enforce(_audit_limiter, request, x_forwarded_for)


async def limit_leads(
    request: Request, x_forwarded_for: str | None = Header(default=None)
) -> None:
    _enforce(_leads_limiter, request, x_forwarded_for)
