"""W8 A3: search-time filters are validated and reach Metapi's task payload.

Stubs only: safe_request_async is replaced, so no provider is called.
"""
from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from app.schemas.discover import SearchParams
from app.services import safe_fetch
from app.services.scraping import metapi_provider as mp
from app.services.scraping.search_filters import metapi_task_filters, normalize_search_filters

FULL = {
    "country": "us",
    "active_status": "Active",
    "media_type": "video",
    "start_date_min": "2026-10-01",
    "start_date_max": "2026-11-01",
    "publisher_platforms": ["instagram", "facebook", "instagram"],
    "content_languages": ["EN"],
    "min_days_active": 30,
}


def test_filters_normalize_and_keep_result_view_keys():
    f = normalize_search_filters(FULL)
    assert f["country"] == "US" and f["active_status"] == "active"
    assert f["publisher_platforms"] == ["facebook", "instagram"]
    assert f["content_languages"] == ["en"]
    assert f["min_days_active"] == 30
    assert normalize_search_filters(None) == {"country": "ALL"}


@pytest.mark.parametrize("bad", [
    {"country": "USA"},
    {"active_status": "paused"},
    {"media_type": "carousel"},
    {"start_date_min": "01/10/2026"},
    {"start_date_min": "2026-11-02", "start_date_max": "2026-11-01"},
    {"publisher_platforms": ["tiktok"]},
    {"content_languages": ["eng"]},
    {"content_languages": ["en", "ar", "fr", "de", "es", "it"]},
])
def test_invalid_filters_are_a_validation_error_before_any_provider_call(bad):
    with pytest.raises(ValidationError):
        SearchParams(query="nike", filters=bad)


def test_keyword_payload_always_has_a_country_and_maps_dates():
    p = metapi_task_filters(FULL, advertiser=False)
    assert p == {
        "country": "US",
        "active_status": "active",
        "media_type": "video",
        "publisher_platforms": ["facebook", "instagram"],
        "content_languages": ["en"],
        "start_date[min]": "2026-10-01",
        "start_date[max]": "2026-11-01",
    }
    assert metapi_task_filters({}, advertiser=False) == {"country": "ALL"}


def test_advertiser_payload_sends_only_explicit_choices():
    assert metapi_task_filters({}, advertiser=True) == {}
    assert metapi_task_filters({"country": "DE", "media_type": "all"}, advertiser=True) == {"country": "DE"}


@pytest.mark.asyncio
async def test_metapi_tasks_carry_the_filters(monkeypatch):
    sent = []

    async def fake(method, url, **kw):
        if method == "POST":
            sent.append(kw.get("json"))
            return httpx.Response(202, json={"task_id": "t1"})
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(200, json={"data": []})

    async def _no_sleep(_s):
        return None

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    monkeypatch.setattr(mp.asyncio, "sleep", _no_sleep)
    provider = mp.MetapiProvider.__new__(mp.MetapiProvider)
    provider.metapi_api_key = "test-key-not-real"
    provider.org_id = None
    await provider.search("15087023444", max_records=15, filters={"country": "US", "media_type": "video"})
    assert sent and sent[0]["advertiser_id"] == "15087023444"
    assert sent[0]["country"] == "US" and sent[0]["media_type"] == "video"
