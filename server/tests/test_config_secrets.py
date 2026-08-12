"""Tests for production secret verification (fail-fast on insecure defaults)."""

import pytest

from app.config import Settings, verify_production_secrets


def _settings(**over) -> Settings:
    base = dict(
        demo_mode=False,
        api_key_hash_salt="a-very-long-random-production-salt",
        admin_token="a-very-long-random-admin-token",
    )
    base.update(over)
    return Settings(**base)


class TestVerifyProductionSecrets:
    def test_demo_mode_skips_all_checks(self):
        # Demo intentionally runs open; defaults must not block startup.
        verify_production_secrets(_settings(demo_mode=True, api_key_hash_salt="change-me-in-production", admin_token=""))

    def test_default_salt_rejected_in_prod(self):
        with pytest.raises(RuntimeError, match="SALT"):
            verify_production_secrets(_settings(api_key_hash_salt="change-me-in-production"))

    def test_short_salt_rejected_in_prod(self):
        with pytest.raises(RuntimeError, match="SALT"):
            verify_production_secrets(_settings(api_key_hash_salt="short"))

    def test_missing_admin_token_rejected_in_prod(self):
        with pytest.raises(RuntimeError, match="ADMIN_TOKEN"):
            verify_production_secrets(_settings(admin_token=""))

    def test_valid_prod_config_passes(self):
        verify_production_secrets(_settings())
