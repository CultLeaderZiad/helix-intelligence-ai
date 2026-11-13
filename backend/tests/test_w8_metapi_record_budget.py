"""W8: Metapi tasks reserve their records against a monthly budget (Metapi bills records).

No provider is called: safe_request_async is stubbed; the counter test uses
the real database table.
"""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.db.session import async_session_maker
from app.services import provider_budget, safe_fetch
from app.services.scraping import metapi_provider as mp
from app.services.scraping.ad_library_provider import AdLibraryProvider


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _instant(_s):
        return None

    monkeypatch.setattr(mp.asyncio, "sleep", _instant)


def test_free_plan_defaults():
    assert settings.METAPI_RESOLVE_COUNT == 15
    assert settings.DISCOVER_DAILY_PROVIDER_CALL_CAP == 6
    assert settings.DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE == 6
    assert settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY == 3
    assert settings.METAPI_MONTHLY_RECORD_BUDGET == 3000


@pytest.mark.asyncio
async def test_refused_records_stop_the_search_before_any_metapi_request(monkeypatch):
    posted, reserved = [], []

    async def fake(method, url, **kw):
        posted.append(url)
        return httpx.Response(202, json={"task_id": "t1"})

    async def refuse(provider, records, budget, org_id=None):
        reserved.append((provider, records))
        return False

    monkeypatch.setattr(safe_fetch, "safe_request_async", fake)
    monkeypatch.setattr(provider_budget, "reserve_provider_records", refuse)
    chain = AdLibraryProvider()
    chain.metapi_provider.metapi_api_key = "test-key-not-real"
    chain.adyntel_provider.adyntel_api_key = None
    chain.meta_token = None
    chain.apify_token = None
    assert await chain.search("gymshark", max_records=15) == []
    assert posted == []
    assert reserved == [("metapi", settings.METAPI_RESOLVE_COUNT)]
    assert chain.stopped_reason == "budget"


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_monthly_record_counter_refuses_past_the_budget_without_counting_refusals():
    provider = f"test-{__import__('uuid').uuid4().hex[:8]}"
    assert await provider_budget.reserve_provider_records(provider, 15, 40) is True
    assert await provider_budget.reserve_provider_records(provider, 15, 40) is True
    assert await provider_budget.reserve_provider_records(provider, 15, 40) is False
    async with async_session_maker() as db:
        used = (await db.execute(text(
            "SELECT records FROM provider_record_budget WHERE provider = :p "
            "AND period_start = date_trunc('month', now() AT TIME ZONE 'utc')::date"
        ), {"p": provider})).scalar_one()
    assert used == 30
    assert await provider_budget.reserve_provider_records(provider, 15, 0) is False
