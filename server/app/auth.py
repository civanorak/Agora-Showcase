import secrets

from fastapi import HTTPException

from .config import settings


def require_admin(authorization: str) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="Not found")
    expected = f"Bearer {settings.admin_token}"
    # Constant-time compare: a plain `!=` short-circuits on the first mismatched
    # byte, leaking the token prefix through response timing. compare_digest
    # takes the same time regardless of where the strings diverge.
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=403, detail="Forbidden")


def require_read_access(authorization: str) -> None:
    """Gate for dashboard read endpoints (/events, /events/stream, /stats).

    Open during a local demo (AGORA_DEMO_MODE=1) so the demo dashboard can poll
    freely. On a public host (demo off) these expose one merchant's traffic to
    anyone, so they require the admin token — same contract as /leads and /sites.
    """
    if settings.demo_mode:
        return
    require_admin(authorization)
