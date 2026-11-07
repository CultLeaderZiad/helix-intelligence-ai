"""W8: a global hard stop for paid provider calls.

The kill switch and the daily provider call cap stop paid calls across every
workspace; a stopped search is refunded, and the query translation model call
never runs for a workspace that cannot pay. No real provider is called here.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.organization import Organization
from app.models.user import User
from app.schemas.discover import SearchParams
from app.services import admin_service, discover_service, monitor_service, provider_budget
from app.services.scraping.ad_library_provider import AdLibraryProvider


def _provider_with_metapi_key(monkeypatch) -> AdLibraryProvider:
    provider = AdLibraryProvider()
    provider.metapi_provider.metapi_api_key = "test-key-not-real"
    provider.adyntel_provider.adyntel_api_key = None
    provider.meta_token = None
    provider.apify_token = None

    async def _must_not_call(*_a, **_kw):
        raise AssertionError("a paid provider was called after the budget refused it")

    monkeypatch.setattr(provider.metapi_provider, "search", _must_not_call)
    return provider


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", [provider_budget.BUDGET, provider_budget.PAUSED])
async def test_a_refused_reservation_stops_the_chain_before_any_paid_call(monkeypatch, reason):
    async def _refuse(_provider, org_id=None):
        return reason

    monkeypatch.setattr(provider_budget, "reserve_provider_call", _refuse)
    provider = _provider_with_metapi_key(monkeypatch)
    assert await provider.search("nike", max_records=5) == []
    assert provider.stopped_reason == reason
    assert provider.provider_outage is False


@pytest.mark.asyncio
async def test_pausing_discover_stops_monitor_scheduling(monkeypatch):
    monkeypatch.setattr(settings, "DISCOVER_ENABLED", False)
    result = await monitor_service.tick()
    assert result["paused"] is True and result["dispatched"] == 0


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_the_daily_counter_refuses_past_the_cap_without_counting_refusals(monkeypatch):
    async with async_session_maker() as db:
        before = (await db.execute(text(
            "SELECT coalesce((SELECT calls FROM provider_call_budget WHERE day = (now() AT TIME ZONE 'utc')::date), 0)"
        ))).scalar_one()
    monkeypatch.setattr(settings, "DISCOVER_DAILY_PROVIDER_CALL_CAP", before + 2)
    results = [await provider_budget.reserve_provider_call("test") for _ in range(3)]
    assert results == [None, None, provider_budget.BUDGET]
    async with async_session_maker() as db:
        after = (await db.execute(text(
            "SELECT calls FROM provider_call_budget WHERE day = (now() AT TIME ZONE 'utc')::date"
        ))).scalar_one()
    assert after == before + 2

    monkeypatch.setattr(settings, "DISCOVER_ENABLED", False)
    assert await provider_budget.reserve_provider_call("test") == provider_budget.PAUSED
    monkeypatch.setattr(settings, "DISCOVER_ENABLED", True)
    monkeypatch.setattr(settings, "DISCOVER_DAILY_PROVIDER_CALL_CAP", 0)
    assert await provider_budget.reserve_provider_call("test") == provider_budget.BUDGET


async def _granted_workspace(credits: float) -> str:
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        admin = User(id=f"pba_{s}", email=f"w8-pb-admin-{s}@example.com", password_hash="x",
                     role="admin", is_platform_admin=True)
        user = User(id=f"pbu_{s}", email=f"w8-pb-{s}@example.com", password_hash="x", role="customer")
        db.add_all([admin, user])
        await db.flush()
        db.add(Organization(id=f"pbo_{s}", name="Budget", owner_id=user.id, plan="trial",
                            plan_id="plan_trial_default", credit_balance=credits))
        await db.commit()
        await admin_service.grant_organization_access(db, admin, f"pbo_{s}", "plan_trial_default", {"discover": True})
    return user.id


@pytest.mark.asyncio
async def test_no_translation_model_call_for_a_workspace_without_credits(monkeypatch):
    user_id = await _granted_workspace(credits=0.0)
    calls = []

    async def _record(query, lang, **_kw):
        calls.append(query)
        return query

    monkeypatch.setattr(discover_service, "translate_search_query", _record)
    async with async_session_maker() as db:
        with pytest.raises(HTTPException) as refused:
            await discover_service.trigger_search(db, SearchParams(query="nike عروض", query_language="ar"), user_id)
    assert refused.value.status_code == 402
    assert calls == []


@pytest.mark.asyncio
async def test_paused_discover_and_overlong_queries_are_refused_before_any_charge(monkeypatch):
    user_id = await _granted_workspace(credits=5.0)
    async with async_session_maker() as db:
        with pytest.raises(HTTPException) as too_long:
            await discover_service.trigger_search(db, SearchParams(query="x" * 301), user_id)
        assert too_long.value.status_code == 422
        assert too_long.value.detail["code"] == "query_too_long"

        monkeypatch.setattr(settings, "DISCOVER_ENABLED", False)
        with pytest.raises(HTTPException) as paused:
            await discover_service.trigger_search(db, SearchParams(query="nike"), user_id)
        assert paused.value.status_code == 503
        assert paused.value.detail["code"] == "discover_paused"

        balance = (await db.execute(text(
            "SELECT credit_balance FROM organizations WHERE owner_id = :u"
        ), {"u": user_id})).scalar_one()
    assert balance == 5.0
