"""Whop billing: membership events grant, renew and revoke access. Database."""
from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.tenancy import apply_tenant_context, tenant_scope
from app.db.session import async_session_maker
from app.models.access_grant import OrganizationAccessGrant
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.user import User
from app.services import billing_service, whop_billing


async def _setup(db, s):
    user = User(id=f"u_wb_{s}", email=f"wb-{s}@example.com", password_hash="x", role="member")
    db.add(user)
    await db.flush()
    org = Organization(id=f"o_wb_{s}", name="WB", owner_id=user.id)
    plan = Plan(id=f"plan_wb_{s}", name="Pro", type="pay_as_you_go",
                feature_flags={"discover": True, "monitors": True, "public_api": True})
    db.add_all([org, plan])
    await db.commit()
    return user, org, plan


def _event(org_id, membership_id, status, whop_plan, period_end, updated_at, kind="membership.updated"):
    return {
        "id": f"msg_{uuid.uuid4().hex[:8]}", "type": kind,
        "data": {
            "id": membership_id, "status": status, "variant_id": whop_plan,
            "metadata": {"helix_org_id": org_id},
            "current_period_end": period_end, "expires_at": None, "updated_at": updated_at,
        },
    }


async def _send(event, wid=None):
    async with async_session_maker() as db:
        return await whop_billing.handle_event(db, wid or event["id"], event)


async def _state(org_id):
    async with async_session_maker() as db:
        with tenant_scope([org_id], "", platform_admin=False, enforce=True):
            await apply_tenant_context(db)
            return await billing_service.access_status_for_org(db, org_id)


@pytest.fixture
def mapped(monkeypatch):
    s = uuid.uuid4().hex[:8]
    monkeypatch.setattr(settings, "WHOP_PLAN_MAP", f"plan_whop_{s}=plan_wb_{s}")
    monkeypatch.setattr(settings, "WHOP_GRACE_HOURS", 48)
    return s


@pytest.mark.asyncio
async def test_activation_grants_plan_features_until_period_end_plus_grace(mapped):
    s = mapped
    async with async_session_maker() as db:
        _u, org, _p = await _setup(db, s)
    end = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).replace(microsecond=0)
    out = await _send(_event(org.id, f"mem_{s}", "active", f"plan_whop_{s}", end.isoformat(), "2026-11-23T10:00:00Z", "membership.activated"))
    assert out == "granted"
    state = await _state(org.id)
    assert state["status"] == "approved"
    assert state["plan_id"] == f"plan_wb_{s}"
    # Only grantable features; public_api is not one.
    assert state["feature_flags"] == {"discover": True, "monitors": True}
    assert datetime.datetime.fromisoformat(state["expires_at"]) == end + datetime.timedelta(hours=48)


@pytest.mark.asyncio
async def test_duplicate_and_stale_deliveries_change_nothing(mapped):
    s = mapped
    async with async_session_maker() as db:
        _u, org, _p = await _setup(db, s)
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    first = _event(org.id, f"mem_{s}", "active", f"plan_whop_{s}", future, "2026-11-23T10:00:00Z")
    assert await _send(first) == "granted"
    assert await _send(first) == "duplicate"
    older_cancel = _event(org.id, f"mem_{s}", "canceled", f"plan_whop_{s}", future, "2026-11-23T09:00:00Z")
    assert await _send(older_cancel) == "stale"
    assert (await _state(org.id))["status"] == "approved"


@pytest.mark.asyncio
async def test_renewal_extends_the_same_grant_and_cancel_revokes_it(mapped):
    s = mapped
    async with async_session_maker() as db:
        _u, org, _p = await _setup(db, s)
    now = datetime.datetime.now(datetime.timezone.utc)
    p1 = (now + datetime.timedelta(days=30)).isoformat()
    p2 = (now + datetime.timedelta(days=60)).replace(microsecond=0)
    await _send(_event(org.id, f"mem_{s}", "active", f"plan_whop_{s}", p1, "2026-11-23T10:00:00Z"))
    await _send(_event(org.id, f"mem_{s}", "active", f"plan_whop_{s}", p2.isoformat(), "2026-12-23T10:00:00Z"))
    async with async_session_maker() as db:
        with tenant_scope([org.id], "", platform_admin=False, enforce=True):
            await apply_tenant_context(db)
            grants = (await db.execute(select(OrganizationAccessGrant).where(OrganizationAccessGrant.org_id == org.id))).scalars().all()
    assert len(grants) == 1
    assert grants[0].expires_at == p2 + datetime.timedelta(hours=48)
    assert await _send(_event(org.id, f"mem_{s}", "canceled", f"plan_whop_{s}", p2.isoformat(), "2026-12-24T10:00:00Z")) == "revoked"
    assert (await _state(org.id))["status"] == "revoked"


@pytest.mark.asyncio
async def test_cancel_never_touches_an_admin_grant(mapped):
    s = mapped
    async with async_session_maker() as db:
        user, org, plan = await _setup(db, s)
        with tenant_scope([org.id], user.id, platform_admin=False, enforce=True):
            await apply_tenant_context(db)
            db.add(OrganizationAccessGrant(org_id=org.id, plan_id=plan.id, feature_flags={"discover": True},
                                           granted_by_user_id=user.id, expires_at=None))
            await db.commit()
    # A cancellation for a membership that never granted anything.
    out = await _send(_event(org.id, f"mem_{s}", "canceled", f"plan_whop_{s}", None, "2026-11-23T10:00:00Z"))
    assert out == "already_ended"
    assert (await _state(org.id))["status"] == "approved"


@pytest.mark.asyncio
async def test_unmapped_plan_and_missing_workspace_grant_nothing(mapped):
    s = mapped
    async with async_session_maker() as db:
        _u, org, _p = await _setup(db, s)
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    assert await _send(_event(org.id, f"mem_{s}", "active", "plan_unknown", future, "2026-11-23T10:00:00Z")) == "unmapped_plan"
    no_org = _event("", f"mem2_{s}", "active", f"plan_whop_{s}", future, "2026-11-23T10:00:00Z")
    assert await _send(no_org) == "unlinked"
    assert (await _state(org.id))["status"] != "approved"


@pytest.mark.asyncio
async def test_subscriptions_are_invisible_to_another_workspace(mapped):
    """Checked as helix_app, the role production runs as, so RLS applies."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.db.session import worker_engine

    s = mapped
    async with async_session_maker() as db:
        _u, org, _p = await _setup(db, s)
        _u2, other, _p2 = await _setup(db, s + "x")
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    await _send(_event(org.id, f"mem_{s}", "active", f"plan_whop_{s}", future, "2026-11-23T10:00:00Z"))

    engine = create_async_engine(worker_engine.url, connect_args={"statement_cache_size": 0})
    try:
        async with engine.connect() as conn:
            seen = {}
            for scope in (org.id, other.id):
                await conn.execute(text("BEGIN"))
                await conn.execute(text("SET LOCAL ROLE helix_app"))
                await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
                await conn.execute(text("SELECT set_config('helix.platform_admin', '0', true)"))
                await conn.execute(text("SELECT set_config('helix.org_ids', :ids, true)"), {"ids": scope})
                seen[scope] = (await conn.execute(
                    text("SELECT provider_membership_id FROM billing_subscriptions WHERE org_id = :o"), {"o": org.id}
                )).scalars().all()
                await conn.execute(text("COMMIT"))
    finally:
        await engine.dispose()
    assert seen[org.id] == [f"mem_{s}"]
    assert seen[other.id] == []
