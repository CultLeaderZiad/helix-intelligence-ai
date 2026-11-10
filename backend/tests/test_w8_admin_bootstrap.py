"""W8: first platform admin bootstrap is explicit, target-checked and idempotent."""
from __future__ import annotations

import datetime
import importlib.util
import os
import types
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.session import async_session_maker
from app.models.access_grant import OrganizationAccessGrant
from app.models.organization import Organization
from app.models.user import User
from app.services import admin_bootstrap_service as svc
from app.services import admin_service

UTC = datetime.timezone.utc


def _load_script():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "bootstrap_platform_admin.py")
    spec = importlib.util.spec_from_file_location("bootstrap_platform_admin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_requires_an_explicit_user_id_and_target_branch():
    script = _load_script()
    with pytest.raises(SystemExit):
        script.parse_args(["--expect-branch", "local"])
    with pytest.raises(SystemExit):
        script.parse_args(["--user-id", "u1"])
    args = script.parse_args(["--user-id", "u1", "--expect-branch", "local"])
    assert args.apply is False and args.features == "discover"


def test_only_grantable_features_are_accepted():
    assert svc._clean_features(["discover", " swipe_files ", "discover"]) == ["discover", "swipe_files"]
    with pytest.raises(svc.BootstrapError):
        svc._clean_features(["create"])
    with pytest.raises(svc.BootstrapError):
        svc._clean_features(["", " "])


def test_revoked_or_expired_grants_count_as_no_access():
    now = datetime.datetime(2026, 11, 7, tzinfo=UTC)
    grant = types.SimpleNamespace(revoked_at=None, expires_at=None, feature_flags={"discover": True, "create": True})
    assert svc._active_flags(grant, now) == {"discover": True}
    grant.expires_at = now - datetime.timedelta(seconds=1)
    assert svc._active_flags(grant, now) == {}
    grant.expires_at, grant.revoked_at = None, now
    assert svc._active_flags(grant, now) == {}
    assert svc._active_flags(None, now) == {}


async def _account(db, s, *, admin=False):
    user = User(id=f"bu_{s}", email=f"w8-boot-{s}@example.com", password_hash="x",
                role="admin" if admin else "customer", is_platform_admin=admin)
    db.add(user)
    await db.flush()
    db.add(Organization(id=f"bo_{s}", name="Boot", owner_id=user.id, plan="trial", plan_id="plan_trial_default"))
    await db.commit()
    return user


async def _grant_count(db, org_id):
    return (await db.execute(
        select(func.count()).select_from(OrganizationAccessGrant).where(OrganizationAccessGrant.org_id == org_id)
    )).scalar_one()


@pytest.mark.asyncio
async def test_local_target_is_accepted_and_a_wrong_branch_is_refused():
    async with async_session_maker() as db:
        assert await svc.verify_target(db, "local") == "local"
        with pytest.raises(svc.BootstrapError):
            await svc.verify_target(db, "br-production-branch")


@pytest.mark.asyncio
async def test_bootstrap_promotes_grants_and_is_idempotent():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = await _account(db, s)
        plan = await svc.plan_bootstrap(db, user.id, ["discover"])
        assert plan.promote and plan.grant and plan.org_id == f"bo_{s}"
        await svc.apply_bootstrap(db, plan)

        await db.refresh(user)
        assert user.is_platform_admin is True and user.role == "admin"
        assert await _grant_count(db, f"bo_{s}") == 1

        again = await svc.plan_bootstrap(db, user.id, ["discover"])
        assert again.promote is False and again.grant is False
        assert await _grant_count(db, f"bo_{s}") == 1


@pytest.mark.asyncio
async def test_adding_a_feature_keeps_features_already_granted():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = await _account(db, s)
        await svc.apply_bootstrap(db, await svc.plan_bootstrap(db, user.id, ["discover", "monitors"]))
        plan = await svc.plan_bootstrap(db, user.id, ["swipe_files"])
        assert plan.promote is False and plan.grant is True
        assert plan.grant_flags == {"discover": True, "monitors": True, "swipe_files": True}


@pytest.mark.asyncio
async def test_refuses_unknown_accounts_and_workspaces_they_do_not_own():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = await _account(db, s)
        other = await _account(db, s + "x")
        with pytest.raises(svc.BootstrapError):
            await svc.plan_bootstrap(db, f"missing_{s}", ["discover"])
        with pytest.raises(svc.BootstrapError):
            await svc.plan_bootstrap(db, user.id, ["discover"], org_id=f"bo_{s}x")
        assert await _grant_count(db, f"bo_{s}x") == 0
        assert other.is_platform_admin is False


@pytest.mark.asyncio
async def test_an_ordinary_user_still_cannot_grant_their_own_workspace():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = await _account(db, s)
        with pytest.raises(HTTPException) as denied:
            await admin_service.grant_organization_access(db, user, f"bo_{s}", "plan_trial_default", {"discover": True})
        assert denied.value.status_code == 403
        assert await _grant_count(db, f"bo_{s}") == 0
