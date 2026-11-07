"""W8: provider credentials and signed media links stay out of URLs and INFO logs."""
from __future__ import annotations

import logging

import httpx
import pytest

from app.core.observability import quiet_http_client_logs
from app.services import safe_fetch
from app.services.scraping.ad_library_provider import AdLibraryProvider


@pytest.mark.asyncio
async def test_apify_token_is_sent_in_a_header_not_the_url(monkeypatch):
    seen = {}

    async def fake(method, url, **kw):
        seen["url"], seen["headers"] = url, kw.get("headers") or {}
        return httpx.Response(200, json=[])

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    provider = AdLibraryProvider()
    provider.apify_token = "apify-test-token-not-real"
    await provider.query_apify("gymshark", max_records=5)
    assert "apify-test-token-not-real" not in seen["url"]
    assert "token=" not in seen["url"]
    assert seen["headers"].get("Authorization") == "Bearer apify-test-token-not-real"


def test_http_client_request_lines_are_not_logged_at_info():
    quiet_http_client_logs()
    for name in ("httpx", "httpcore"):
        assert not logging.getLogger(name).isEnabledFor(logging.INFO)
        assert logging.getLogger(name).isEnabledFor(logging.WARNING)
