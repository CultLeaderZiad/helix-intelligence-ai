"""W8: zero-ad Discover searches are refunded, without weakening abuse limits.

* Only the search's own discover_job_start charge is refunded, once per job,
  atomically (concurrent settlements refund once).
* Monitor runs and other operations are never refunded by this path.
* Refunds do not lower the per-workspace search or provider-call counters, the
  global provider budget, or attempt counts.
* An identical empty search within the zero-result window reuses the earlier
  job instead of calling a provider again.
No provider is called: providers and translation are stubbed.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.schemas.discover import SearchParams
from app.services import admin_service, billing_service as billing, discover_service, provider_budget

DAY = "(now() AT TIME ZONE 'utc')::date"


async def _workspace(credits: float = 5.0, grant: bool = False) -> tuple[str, str]:
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = User(id=f"zr_{s}", email=f"w8-zero-{s}@example.com", password_hash="x", role="customer")
        db.add(user)
        await db.flush()
        db.add(Organization(id=f"zro_{s}", name="Zero", owner_id=user.id, plan="trial",
                            plan_id="plan_payg_default", credit_balance=credits, daily_credits_used_today=0.0))
        if grant:
            db.add(User(id=f"zra_{s}", email=f"w8-zero-admin-{s}@example.com", password_hash="x",
                        role="admin", is_platform_admin=True))
        await db.commit()
        if grant:
            admin = (await db.execute(select(User).where(User.id == f"zra_{s}"))).scalar_one()
            await admin_service.grant_organization_access(db, admin, f"zro_{s}", "plan_payg_default", {"discover": True})
    return user.id, f"zro_{s}"


async def _job(org_id: str, status: str = "succeeded", records: int = 0) -> str:
    job_id = f"zrj_{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as db:
        db.add(ScrapeJob(id=job_id, org_id=org_id, query="zero test", status=status, record_count=records))
        await db.commit()
    return job_id


async def _charge(org_id: str, user_id: str, job_id: str, operation: str = "discover_job_start") -> None:
    async with async_session_maker() as db:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
        await billing.charge(db=db, org=org, user_id=user_id, amount=1.0, provider="discover_composite",
                             operation=operation, units=1.0, cost_usd=0.0, job_id=job_id, metadata={})


async def _balance(org_id: str) -> tuple[float, float]:
    async with async_session_maker() as db:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
        return round(float(org.credit_balance), 2), round(float(org.daily_credits_used_today), 2)


async def _settle(org_id: str, job_id: str) -> bool:
    async with async_session_maker() as db:
        return await discover_service.refund_zero_result_search(db, org_id, job_id)


@pytest.mark.asyncio
async def test_zero_ad_search_is_refunded_once_on_repeated_settlement():
    user_id, org_id = await _workspace()
    job_id = await _job(org_id)
    await _charge(org_id, user_id, job_id)
    assert await _balance(org_id) == (4.0, 1.0)
    assert await _settle(org_id, job_id) is True
    assert await _settle(org_id, job_id) is False
    assert await _settle(org_id, job_id) is False
    assert await _balance(org_id) == (5.0, 0.0)


@pytest.mark.asyncio
async def test_concurrent_settlements_refund_exactly_once():
    user_id, org_id = await _workspace()
    job_id = await _job(org_id)
    await _charge(org_id, user_id, job_id)
    results = await asyncio.gather(*[_settle(org_id, job_id) for _ in range(4)])
    assert sorted(results) == [False, False, False, True]
    assert await _balance(org_id) == (5.0, 0.0)


@pytest.mark.asyncio
async def test_other_operations_are_never_refunded_by_this_path():
    user_id, org_id = await _workspace()
    monitor_job = await _job(org_id)
    await _charge(org_id, user_id, monitor_job, operation="monitor_run")
    assert await _settle(org_id, monitor_job) is False
    uncharged_job = await _job(org_id)
    assert await _settle(org_id, uncharged_job) is False
    assert await _balance(org_id) == (4.0, 1.0)


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_refunds_do_not_lower_search_or_provider_counters(monkeypatch):
    monkeypatch.setattr(settings, "DISCOVER_DAILY_PROVIDER_CALL_CAP", 10_000_000)
    user_id, org_id = await _workspace()
    job_id = await _job(org_id)
    assert await provider_budget.reserve_search_slot(org_id) is True
    assert await provider_budget.reserve_provider_call("stub", org_id=org_id) is None
    await _charge(org_id, user_id, job_id)

    async def counters():
        async with async_session_maker() as db:
            row = (await db.execute(text(
                f"SELECT searches, provider_calls FROM workspace_daily_usage WHERE day = {DAY} AND org_id = :o"
            ), {"o": org_id})).one()
            total = (await db.execute(text(f"SELECT calls FROM provider_call_budget WHERE day = {DAY}"))).scalar_one()
        return tuple(row), total

    before = await counters()
    assert await _settle(org_id, job_id) is True
    assert await counters() == before
    assert before[0] == (1, 1)


@pytest.mark.asyncio
async def test_daily_search_cap_refuses_and_does_not_count_refusals(monkeypatch):
    monkeypatch.setattr(settings, "DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY", 2)
    _user, org_id = await _workspace()
    assert [await provider_budget.reserve_search_slot(org_id) for _ in range(3)] == [True, True, False]
    async with async_session_maker() as db:
        used = (await db.execute(text(
            f"SELECT searches FROM workspace_daily_usage WHERE day = {DAY} AND org_id = :o"
        ), {"o": org_id})).scalar_one()
    assert used == 2


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_one_workspace_cannot_use_up_the_global_provider_budget(monkeypatch):
    monkeypatch.setattr(settings, "DISCOVER_DAILY_PROVIDER_CALL_CAP", 10_000_000)
    monkeypatch.setattr(settings, "DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE", 1)
    _user, org_id = await _workspace()
    _other_user, other_org = await _workspace()
    assert await provider_budget.reserve_provider_call("stub", org_id=org_id) is None
    assert await provider_budget.reserve_provider_call("stub", org_id=org_id) == provider_budget.WORKSPACE_BUDGET
    assert await provider_budget.reserve_provider_call("stub", org_id=other_org) is None
    async with async_session_maker() as db:
        used = (await db.execute(text(
            f"SELECT provider_calls FROM workspace_daily_usage WHERE day = {DAY} AND org_id = :o"
        ), {"o": org_id})).scalar_one()
    assert used == 1


@pytest.mark.asyncio
async def test_an_identical_empty_search_is_reused_without_a_new_charge(monkeypatch):
    from app.services import work_outbox

    async def _same(query, lang, **_kw):
        return query

    monkeypatch.setattr(discover_service, "translate_search_query", _same)
    monkeypatch.setattr(work_outbox, "inline_execution_enabled", lambda: False)
    user_id, org_id = await _workspace(credits=5.0, grant=True)

    async with async_session_maker() as db:
        first = await discover_service.trigger_search(db, SearchParams(query="no such brand"), user_id)
    async with async_session_maker() as db:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == first.job_id))).scalar_one()
        job.status, job.record_count = "succeeded", 0
        await db.commit()
    async with async_session_maker() as db:
        assert await discover_service.refund_zero_result_search(db, org_id, first.job_id) is True
    balance_after_refund = await _balance(org_id)

    async with async_session_maker() as db:
        second = await discover_service.trigger_search(db, SearchParams(query="no such brand"), user_id)
    assert second.job_id == first.job_id
    assert await _balance(org_id) == balance_after_refund
    async with async_session_maker() as db:
        searches = (await db.execute(text(
            f"SELECT searches FROM workspace_daily_usage WHERE day = {DAY} AND org_id = :o"
        ), {"o": org_id})).scalar_one()
    assert searches == 1
