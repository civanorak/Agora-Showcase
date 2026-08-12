"""Tests for admin auth, incl. constant-time token comparison."""

from unittest.mock import patch

import pytest

from app import auth
from app.auth import require_admin
from app.config import settings
from fastapi import HTTPException


@pytest.fixture
def admin_token():
    prev = settings.admin_token
    settings.admin_token = "correct-horse-battery-staple"
    yield settings.admin_token
    settings.admin_token = prev


def test_unset_token_returns_404():
    prev = settings.admin_token
    settings.admin_token = ""
    try:
        with pytest.raises(HTTPException) as exc:
            require_admin("Bearer anything")
        assert exc.value.status_code == 404
    finally:
        settings.admin_token = prev


def test_correct_token_passes(admin_token):
    require_admin(f"Bearer {admin_token}")  # no exception


def test_wrong_token_forbidden(admin_token):
    with pytest.raises(HTTPException) as exc:
        require_admin("Bearer wrong-token")
    assert exc.value.status_code == 403


def test_uses_constant_time_comparison(admin_token):
    """Guard against a regression back to a short-circuiting `!=` compare."""
    with patch.object(auth.secrets, "compare_digest", wraps=auth.secrets.compare_digest) as spy:
        require_admin(f"Bearer {admin_token}")
    spy.assert_called_once()
