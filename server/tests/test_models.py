"""Edge-case validation tests for app.models — the truncation/capping paths."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import _HEADERS_MAX_BYTES, _UA_MAX_BYTES, EventDB, EventIn


class TestEventInUA:
    def test_user_agent_alias_populates_ua(self):
        e = EventIn(method="GET", path="/", status=200, user_agent="curl/8")
        assert e.ua == "curl/8"

    def test_non_string_ua_becomes_empty(self):
        e = EventIn(method="GET", path="/", status=200, ua=12345)
        assert e.ua == ""

    def test_oversized_ua_is_truncated_to_cap(self):
        e = EventIn(method="GET", path="/", status=200, ua="a" * (_UA_MAX_BYTES + 500))
        assert len(e.ua.encode("utf-8")) <= _UA_MAX_BYTES

    def test_ua_under_cap_is_unchanged(self):
        e = EventIn(method="GET", path="/", status=200, ua="short-ua")
        assert e.ua == "short-ua"


class TestEventInHeaders:
    def test_non_dict_headers_becomes_empty(self):
        e = EventIn(method="GET", path="/", status=200, headers="not-a-dict")
        assert e.headers == {}

    def test_small_headers_pass_through(self):
        e = EventIn(method="GET", path="/", status=200, headers={"a": "1"})
        assert e.headers == {"a": "1"}

    def test_oversized_headers_are_trimmed_to_fit(self):
        big = {f"k{i}": "v" * 200 for i in range(200)}
        e = EventIn(method="GET", path="/", status=200, headers=big)
        import json

        assert len(json.dumps(e.headers).encode()) <= _HEADERS_MAX_BYTES
        assert len(e.headers) < len(big)


class TestEventInConstraints:
    def test_status_below_100_rejected(self):
        with pytest.raises(ValidationError):
            EventIn(method="GET", path="/", status=99)

    def test_status_above_599_rejected(self):
        with pytest.raises(ValidationError):
            EventIn(method="GET", path="/", status=600)


class TestEventDB:
    def test_eventdb_roundtrip(self):
        row = EventDB(
            id=1,
            site_id="s1",
            ts=datetime(2026, 7, 20, 12, 0, 0),
            method="GET",
            path="/x",
            status=200,
            ua="ua",
        )
        assert row.id == 1
        assert row.ip_hash is None
        assert row.headers == {}
        assert row.beacon_seen is False
