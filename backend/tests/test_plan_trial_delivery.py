"""A visitor who picks a plan gets that plan's features, through the real path.

sign-up (with plan_id) -> sign-in -> /api/auth/session flags -> a gated route,
then the end of the trial (plus grace) and a paid subscription. No shortcut:
every check goes through the HTTP API the app uses.
"""
from __future__ import annotations

import datetime
import re
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.core.tenancy import apply_tenant_context, tenant_scope
from app.db.session import async_session_maker
from app.main import app
from app.models.access_grant import OrganizationAccessGrant
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.user import User
from app.services import whop_billing


@pytest.fixture(autouse=True)
def _trial_on(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "SIGNUP_TRIAL_DAYS", 7)
    monkeypatch.setattr(settings, "TRIAL_GRACE_HOURS", 12)
    monkeypatch.setattr(settings, "SIGNUP_TRIAL_FEATURES", ("discover", "swipe_files", "monitors"))


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")


def _card(**extra):
    return {"listed": True, "order": 1, "tagline": {"en": "t", "ar": "ت"}, **extra}


async def _plans():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        db.add_all([
            # Has team accounts but not monitors: different from the default trial both ways.
            Plan(id=f"plan_a_{s}", name="Agency-like", type="pro", price_monthly=99.99,
                 feature_flags={"discover": True, "swipe_files": True, "team_accounts": True},
                 pricing=_card(), limits={"records_per_month": 5000, "monitors": 15}),
            Plan(id=f"plan_b_{s}", name="Pro-like", type="pro", price_monthly=49.99,
                 feature_flags={"discover": True, "swipe_files": True, "monitors": True}, pricing=_card()),
            Plan(id=f"plan_unlisted_{s}", name="Hidden", type="pro", price_monthly=1.0,
                 feature_flags={"team_accounts": True, "discover": True}, pricing={"listed": False}),
            Plan(id=f"plan_notrial_{s}", name="No trial", type="pro", price_monthly=5.0,
                 feature_flags={"team_accounts": True, "discover": True}, pricing=_card(trial_days=0)),
            Plan(id=f"plan_short_{s}", name="Two days", type="pro", price_monthly=5.0,
                 feature_flags={"discover": True, "swipe_files": True}, pricing=_card(trial_days=2)),
        ])
        await db.commit()
    return s


async def _sign_up(client, plan_id=None):
    s = uuid.uuid4().hex[:10]
    email, password = f"pt-{s}@example.com", f"Plan-{s}-Pw1!"
    body = {"email": email, "password": password, "name": "Trial"}
    if plan_id:
        body["plan_id"] = plan_id
    assert (await client.post("/api/auth/sign-up", json=body)).status_code == 202
    session = (await client.post("/api/auth/sign-in", json={"email": email, "password": password})).json()
    return session, {"Authorization": f"Bearer {session['access_token']}"}


async def _monitors_status(client, headers):
    return (await client.get("/api/monitors", headers=headers)).status_code


@pytest.mark.asyncio
async def test_picked_plan_features_arrive_in_the_session_and_gate_real_routes():
    s = await _plans()
    async with _client() as client:
        agency, agency_h = await _sign_up(client, f"plan_a_{s}")
        assert agency["access_status"] == "approved"
        assert agency["feature_flags"]["team_accounts"] is True      # the picked plan's feature
        assert agency["feature_flags"].get("monitors") is not True    # and only its features
        assert await _monitors_status(client, agency_h) == 403

        pro, pro_h = await _sign_up(client, f"plan_b_{s}")
        assert pro["feature_flags"]["monitors"] is True
        assert pro["feature_flags"].get("team_accounts") is not True
        assert await _monitors_status(client, pro_h) == 200

        default, default_h = await _sign_up(client)  # no plan picked: the default trial
        assert default["feature_flags"]["monitors"] is True and default["feature_flags"].get("team_accounts") is not True
        assert await _monitors_status(client, default_h) == 200


@pytest.mark.asyncio
async def test_unlisted_or_unknown_plans_cannot_be_picked_and_no_trial_plans_use_the_default():
    s = await _plans()
    async with _client() as client:
        for pid in (f"plan_unlisted_{s}", f"plan_notrial_{s}", "plan_does_not_exist", "x" * 300):
            session, _ = await _sign_up(client, pid)
            assert session["feature_flags"].get("team_accounts") is not True, pid
            assert session["feature_flags"]["monitors"] is True, pid  # the default trial


async def _grant_for(email):
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one()
        with tenant_scope([org.id], user.id, platform_admin=False, enforce=True):
            await apply_tenant_context(db)
            grant = (await db.execute(select(OrganizationAccessGrant).where(OrganizationAccessGrant.org_id == org.id))).scalars().one()
            return user, org, grant


@pytest.mark.asyncio
async def test_trial_lasts_its_days_plus_the_12_hour_grace_then_everything_stops():
    s = await _plans()
    async with _client() as client:
        session, headers = await _sign_up(client, f"plan_short_{s}")
        user, org, grant = await _grant_for(session["email"])
        end = user.trial_expires_at
        assert (end - user.trial_started_at) == datetime.timedelta(days=2)  # the plan's own trial length
        assert grant.expires_at - end == datetime.timedelta(hours=12)       # grace after the real end
        assert session["feature_flags"]["swipe_files"] is True

        # Past the grace: no access and no features, and gated routes refuse.
        async with async_session_maker() as db:
            with tenant_scope([org.id], user.id, platform_admin=False, enforce=True):
                await apply_tenant_context(db)
                await db.execute(update(OrganizationAccessGrant).where(OrganizationAccessGrant.id == grant.id)
                                 .values(expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)))
                await db.commit()
        again = (await client.get("/api/auth/session", headers=headers)).json()
        assert again["access_status"] == "expired" and not any(again["feature_flags"].values())
        assert await _monitors_status(client, headers) == 403


@pytest.mark.asyncio
async def test_paying_after_the_trial_delivers_the_paid_plans_features(monkeypatch):
    s = await _plans()
    monkeypatch.setattr(settings, "WHOP_PLAN_MAP", f"plan_whop_x{s}=plan_b_{s}")
    async with _client() as client:
        session, headers = await _sign_up(client, f"plan_a_{s}")
        user, org, grant = await _grant_for(session["email"])
        async with async_session_maker() as db:
            with tenant_scope([org.id], user.id, platform_admin=False, enforce=True):
                await apply_tenant_context(db)
                await db.execute(update(OrganizationAccessGrant).where(OrganizationAccessGrant.id == grant.id)
                                 .values(expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)))
                await db.commit()
        assert await _monitors_status(client, headers) == 403  # trial over

        period_end = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
        event = {"id": f"msg1_{s}", "type": "membership.activated", "data": {
            "id": f"mem_{s}", "status": "active", "variant_id": f"plan_whop_x{s}", "updated_at": "2026-11-24T10:00:00Z",
            "metadata": {"helix_org_id": org.id}, "current_period_end": period_end}}
        async with async_session_maker() as db:
            assert await whop_billing.handle_event(db, f"wh1_{s}", event) == "granted"
        paid = (await client.get("/api/auth/session", headers=headers)).json()
        assert paid["access_status"] == "approved" and paid["feature_flags"]["monitors"] is True
        assert await _monitors_status(client, headers) == 200

        event["data"].update(status="canceled", updated_at="2026-11-25T10:00:00Z")
        async with async_session_maker() as db:
            assert await whop_billing.handle_event(db, f"wh2_{s}", event) == "revoked"
        ended = (await client.get("/api/auth/session", headers=headers)).json()
        assert not any(ended["feature_flags"].values())
        assert await _monitors_status(client, headers) == 403


@pytest.mark.asyncio
async def test_public_pricing_shows_each_plans_real_details():
    s = await _plans()
    async with _client() as client:
        data = (await client.get("/api/public/pricing")).json()
    plans = {p["id"]: p for p in data["plans"]}
    a, short = plans[f"plan_a_{s}"], plans[f"plan_short_{s}"]
    assert f"plan_unlisted_{s}" not in plans
    assert a["feature_flags"] == ["discover", "swipe_files", "team_accounts"]
    assert a["limits"]["records_per_month"] == 5000 and a["limits"]["monitors"] == 15
    assert a["trial_days"] == 7 and short["trial_days"] == 2 and plans[f"plan_notrial_{s}"]["trial_days"] == 0
    assert a["price_monthly"] == 99.99


def test_no_user_facing_backend_text_names_the_payment_provider():
    root = Path(__file__).resolve().parents[1] / "app"
    offenders = []
    for name in ("services/whop_billing.py", "api/routers/billing_webhooks.py", "api/routers/account.py"):
        text = (root / name).read_text(encoding="utf-8")
        for match in re.finditer(r'"(?:message|detail)"\s*:\s*"([^"]*)"', text):
            if "whop" in match.group(1).lower():
                offenders.append((name, match.group(1)))
    assert offenders == []
