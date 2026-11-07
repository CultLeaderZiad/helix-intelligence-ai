"""W8: Metapi request shape, advertiser search, and unfinished tasks.

Found by the Discover proof: keyword results are mostly look-alike sellers, so
a brand query resolves the brand's own advertiser page and loads its ads.
No network: safe_request_async is stubbed.
"""
from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services import provider_budget, safe_fetch
from app.services.scraping import metapi_provider as mp
from app.services.scraping.metapi_provider import MetapiProvider


def _ad(page_id: str, page_name: str, body: str = "Ad copy") -> dict:
    return {
        "provider_id": 1, "provider_page_id": page_id, "provider_page_name": page_name,
        "bodies": [body], "creative_link_titles": [], "captions": [], "original_image_url": ["https://x.fbcdn.net/a.jpg"],
        "creation_time": "2026-10-01T00:00:00Z",
    }


def _provider() -> MetapiProvider:
    provider = MetapiProvider(None, "", "")
    provider.metapi_api_key = "test-key-not-real"
    return provider


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _instant(_s):
        return None

    monkeypatch.setattr(mp.asyncio, "sleep", _instant)


def _fake_metapi(monkeypatch, results_by_payload):
    """results_by_payload(payload) -> list of ads for that task."""
    tasks, posted = {}, []

    async def fake(method, url, **kw):
        if method == "POST":
            posted.append(kw["json"])
            task_id = f"t{len(posted)}"
            tasks[task_id] = results_by_payload(kw["json"])
            return httpx.Response(202, json={"task_id": task_id, "status": "running"})
        task_id = url.split("/tasks/")[1].split("/")[0]
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(200, json={"data": tasks[task_id], "pagination": {"total": len(tasks[task_id])}})

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    return posted


def test_page_ids_and_ad_library_links_are_recognised():
    assert mp.page_id_from_query("15087023444") == "15087023444"
    link = "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=15087023444"
    assert mp.page_id_from_query(link) == "15087023444"
    assert mp.page_id_from_query("nike") is None
    assert mp.page_id_from_query("https://www.facebook.com/ads/library/?q=nike") is None
    assert mp.page_id_from_query("123") is None


def test_brand_terms_and_page_matching_never_take_a_reseller():
    assert mp.brand_term("https://www.Nike.com/shoes") == "nike"
    assert mp.brand_term("nike.com") == "nike"
    assert mp.brand_term("Real Madrid") == "real madrid"
    ads = [_ad("111111", "Nike Shoes PH"), _ad("222222", "Nike"), _ad("222222", "Nike"), _ad("333333", "Sneaker Hub")]
    assert mp.pick_brand_page(ads, "nike") == ("222222", "Nike")
    assert mp.pick_brand_page([_ad("444444", "Gymshark Official")], "gymshark") == ("444444", "Gymshark Official")
    assert mp.pick_brand_page([_ad("111111", "Nike Shoes PH")], "nike") is None


@pytest.mark.asyncio
async def test_a_brand_query_loads_the_brands_own_page(monkeypatch):
    def results(payload):
        if "advertiser_id" in payload:
            return [_ad("222222", "Nike", f"Own ad {i}") for i in range(3)]
        return [_ad("111111", "Nike Shoes PH"), _ad("222222", "Nike")]

    posted = _fake_metapi(monkeypatch, results)
    reserved = []

    async def _reserve(name, org_id=None):
        reserved.append(name)
        return None

    monkeypatch.setattr(provider_budget, "reserve_provider_call", _reserve)
    provider = _provider()
    ads = await provider.search("nike.com", max_records=15)

    assert posted[0] == {"q": "nike", "country": "ALL", "count": settings.METAPI_RESOLVE_COUNT, "search_type": "keyword_exact_phrase"}
    assert posted[1] == {"advertiser_id": "222222", "count": 15}
    assert reserved == ["Metapi advertiser"]
    assert provider.last_mode == "advertiser" and provider.resolved_page_name == "Nike"
    assert len(ads) == 3 and {a.brand_name for a in ads} == {"Nike"}


@pytest.mark.asyncio
async def test_no_matching_page_keeps_keyword_results_with_one_task(monkeypatch):
    posted = _fake_metapi(monkeypatch, lambda payload: [_ad("111111", "Nike Shoes PH")])
    provider = _provider()
    ads = await provider.search("nike", max_records=15)
    assert len(posted) == 1 and provider.last_mode == "keyword" and len(ads) == 1


@pytest.mark.asyncio
async def test_the_daily_cap_stops_the_second_task(monkeypatch):
    posted = _fake_metapi(monkeypatch, lambda payload: [_ad("222222", "Nike")])

    async def _refuse(_name, org_id=None):
        return provider_budget.BUDGET

    monkeypatch.setattr(provider_budget, "reserve_provider_call", _refuse)
    provider = _provider()
    await provider.search("nike", max_records=15)
    assert len(posted) == 1 and provider.last_mode == "keyword"


@pytest.mark.asyncio
async def test_a_page_link_goes_straight_to_the_advertiser_search(monkeypatch):
    posted = _fake_metapi(monkeypatch, lambda payload: [_ad("222222", "Nike")])
    provider = _provider()
    await provider.search("https://www.facebook.com/ads/library/?view_all_page_id=222222", max_records=15)
    assert posted == [{"advertiser_id": "222222", "count": 15}]
    assert provider.last_mode == "advertiser" and provider.resolved_page_name == "Nike"


@pytest.mark.asyncio
async def test_an_unfinished_task_is_a_failure_and_results_are_never_requested(monkeypatch):
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
