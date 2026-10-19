"""Fail closed for unavailable robots; only real missing files have no rules."""
from unittest.mock import patch

import httpx
import pytest

from app.services import scrapling_engine as engine


@pytest.fixture(autouse=True)
def clear_robots_cache():
    engine._ROBOTS_CACHE.clear()
    yield
    engine._ROBOTS_CACHE.clear()


@pytest.mark.parametrize("status", [404, 410])
def test_missing_robots_allows(status):
    with patch("app.services.security_service.is_safe_public_url", return_value=True), patch(
        "app.services.safe_fetch.safe_request", return_value=httpx.Response(status)
    ) as request:
        assert engine.robots_allowed("https://example.com/page")
        assert engine.robots_allowed("https://example.com/other")
        assert request.call_count == 1


@pytest.mark.parametrize("outcome", [httpx.Response(500), httpx.Response(503), httpx.ReadTimeout("test timeout"), RuntimeError("test error"), httpx.Response(403)])
def test_unavailable_robots_blocks_and_caches(outcome):
    kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
    with patch("app.services.security_service.is_safe_public_url", return_value=True), patch(
        "app.services.safe_fetch.safe_request", **kwargs
    ) as request:
        result = engine.fetch("https://example.com/page")
        assert result["fetch_status"] == "blocked"
        assert result["reason"] == "robots_unavailable"
        assert result["html"] is None
        assert not engine.robots_allowed("https://example.com/other")
        assert request.call_count == 1


def test_explicit_disallow_has_distinct_reason():
    with patch("app.services.security_service.is_safe_public_url", return_value=True), patch(
        "app.services.safe_fetch.safe_request", return_value=httpx.Response(200, content=b"User-agent: *\nDisallow: /\n")
    ):
        assert engine.fetch("https://example.com/page")["reason"] == "robots_disallow"


def test_deny_expires_after_same_ttl_as_allow():
    with patch("app.services.security_service.is_safe_public_url", return_value=True), patch(
        "app.services.safe_fetch.safe_request", side_effect=[httpx.Response(503), httpx.Response(404)]
    ) as request, patch.object(engine.time, "monotonic", return_value=1) as clock:
        assert not engine.robots_allowed("https://example.com/page")
        clock.return_value = 2
        assert not engine.robots_allowed("https://example.com/page")
        clock.return_value = 1 + engine._ROBOTS_TTL_S + 1
        assert engine.robots_allowed("https://example.com/page")
        assert request.call_count == 2
