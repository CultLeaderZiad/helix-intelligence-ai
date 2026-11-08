"""W8: plan limits (plans.limits) are enforced on the server.

searches_per_day overrides the global per-workspace search cap (and doubles
into the provider-call cap); monitors and monitor_cadences gate monitor
creation and reactivation. Plans without limits keep the global defaults.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.user import User
from app.schemas.pricing import PlanLimits
from app.services import monitor_service, provider_budget


def test_limits_schema_bounds_and_cadences():
    limits = PlanLimits(searches_per_day=5, monitors=2, monitor_cadences=["weekly", "weekly"])
    assert limits.monitor_cadences == ["weekly"]
    assert PlanLimits().searches_per_day is None
    with pytest.raises(ValidationError):
        PlanLimits(monitor_cadences=["hourly"])
    with pytest.raises(ValidationError):
        PlanLimits(searches_per_day=-1)


def test_caps_fall_back_to_global_settings():
    assert provider_budget.search_cap({}) == settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY
    assert provider_budget.search_cap({"searches_per_day": 20}) == 20
    assert provider_budget.workspace_call_cap({}) == settings.DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE
    assert provider_budget.workspace_call_cap({"searches_per_day": 20}) == 40
    assert provider_budget.workspace_call_cap({"searches_per_day": 1}) == settings.DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE


async def _workspace(limits: dict | None) -> tuple[User, str]:
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        plan = Plan(id=f"plan_lim_{s}", name="Limited", type="custom", feature_flags={"monitors": True}, limits=limits)
        user = User(id=f"plu_{s}", email=f"w8-limits-{s}@example.com", password_hash="x", role="customer")
        db.add_all([plan, user])
        await db.flush()
        db.add(Organization(id=f"plo_{s}", name="Limits", owner_id=user.id, plan="custom", plan_id=plan.id))
        await db.commit()
    return user, f"plo_{s}"


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_plan_search_cap_overrides_the_global_cap():
    _user, org_id = await _workspace({"searches_per_day": 2})
    assert await provider_budget.reserve_search_slot(org_id) is True
    assert await provider_budget.reserve_search_slot(org_id) is True
    assert await provider_budget.reserve_search_slot(org_id) is False

    _user, zero_org = await _workspace({"searches_per_day": 0})
    assert await provider_budget.reserve_search_slot(zero_org) is False

    async with async_session_maker() as db:
        assert await provider_budget.plan_limits(db, zero_org) == {"searches_per_day": 0}
        _u, open_org = await _workspace(None)
        assert await provider_budget.plan_limits(db, open_org) == {}


@pytest.mark.asyncio
async def test_plan_monitor_count_and_cadence_are_enforced():
    user, org_id = await _workspace({"monitors": 1, "monitor_cadences": ["weekly"]})
    async with async_session_maker() as db:
        with pytest.raises(HTTPException) as cadence:
            await monitor_service.create_monitor(db, user=user, org_id=org_id, name="A", query="gymshark", cadence="daily")
        assert cadence.value.status_code == 403
        assert cadence.value.detail["code"] == "plan_cadence_not_allowed"

        first = await monitor_service.create_monitor(db, user=user, org_id=org_id, name="A", query="gymshark", cadence="weekly")
        with pytest.raises(HTTPException) as count:
            await monitor_service.create_monitor(db, user=user, org_id=org_id, name="B", query="nike", cadence="weekly")
        assert count.value.detail["code"] == "plan_monitor_limit"

        with pytest.raises(HTTPException):
            await monitor_service.update_monitor(db, first["id"], org_id, {"cadence": "daily"})
        paused = await monitor_service.update_monitor(db, first["id"], org_id, {"status": "paused"})
        assert paused["status"] == "paused"
        second = await monitor_service.create_monitor(db, user=user, org_id=org_id, name="B", query="nike", cadence="weekly")
        with pytest.raises(HTTPException) as reactivate:
            await monitor_service.update_monitor(db, first["id"], org_id, {"status": "active"})
        assert reactivate.value.detail["code"] == "plan_monitor_limit"
        assert second["status"] == "active"


@pytest.mark.asyncio
async def test_plans_without_limits_keep_todays_behaviour():
    user, org_id = await _workspace(None)
    async with async_session_maker() as db:
        for i in range(3):
            created = await monitor_service.create_monitor(
                db, user=user, org_id=org_id, name=f"M{i}", query=f"brand{i}", cadence="daily"
            )
            assert created["cadence"] == "daily"
