"""W8: Metapi request shape and unfinished tasks (found by the Discover proof)."""
from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services import safe_fetch
from app.services.scraping.metapi_provider import MetapiProvider


def _provider() -> MetapiProvider:
    provider = MetapiProvider(None, "", "")
    provider.metapi_api_key = "test-key-not-real"
    return provider


@pytest.fixture
def no_sleep(monkeypatch):
    import app.services.scraping.metapi_provider as module

    async def _instant(_s):
        return None

    monkeypatch.setattr(module.asyncio, "sleep", _instant)


@pytest.mark.asyncio
async def test_task_asks_for_only_the_ads_helix_keeps_with_exact_phrase(monkeypatch, no_sleep):
    sent = {}

    async def fake(method, url, **kw):
        if method == "POST":
            sent.update(kw["json"])
            return httpx.Response(202, json={"task_id": "t1", "status": "running"})
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(200, json={"data": [], "pagination": {"total": 0}})

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    await _provider().search("gymshark", max_records=15)
    assert sent["count"] == 15
    assert sent["search_type"] == "keyword_exact_phrase"
    assert sent["q"] == "gymshark"


@pytest.mark.asyncio
async def test_an_unfinished_task_is_a_failure_and_results_are_never_requested(monkeypatch, no_sleep):
    calls = []

    async def fake(method, url, **kw):
        calls.append(url)
        if method == "POST":
            return httpx.Response(202, json={"task_id": "t2", "status": "running"})
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "running"})
        raise AssertionError("results requested for an unfinished task")

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    monkeypatch.setattr(settings, "METAPI_POLL_TIMEOUT_S", 0.05)
    provider = _provider()
    assert await provider.search("gymshark", max_records=15) == []
    assert provider.last_outcome == "failure"
    assert not any(u.endswith("/results") for u in calls)
