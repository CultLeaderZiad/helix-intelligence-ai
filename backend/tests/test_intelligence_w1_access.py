"""Manual access grants: request, approve, revoke, expiry, and worker re-check."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.leadgen import LeadGenJob
from app.models.scout import ScoutJob, ScoutMapsJob
from app.models.user import User
from app.services.admin_service import (
    approve_access_request,
    grant_organization_access,
    reject_access_request,
    revoke_organization_access,
    submit_access_request,
)
from app.services.billing_service import access_status_for_org, assert_can_spend
from app.services.leadgen_pipeline import run_leadgen_job
from app.services.maps_scout_service import run_maps_scout_worker
from app.services.scout_service import run_scout_job_worker


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _people(db, suffix):
    admin = User(
        id=f"adm_{suffix}",
        email=f"adm_{suffix}@example.com",
        password_hash="x",
        role="admin",
        is_platform_admin=True,
    )
    owner = User(
        id=f"own_{suffix}",
        email=f"own_{suffix}@example.com",
        password_hash="x",
        role="customer",
        is_platform_admin=False,
    )
    db.add_all([admin, owner])
    await db.flush()
    org = Organization(
        id=f"org_{suffix}",
        name="Workspace",
        owner_id=owner.id,
        plan_id="plan_trial_default",
        plan="trial",
        status="active",
        credit_balance=20,
    )
    plan = Plan(
        id=f"plan_{suffix}",
        name="Granted",
        type="pay_as_you_go",
        feature_flags={
            "discover": True,
            "intelligence": True,
            "create": True,
            "scout": False,
            "leadgen": False,
            "monitors": False,
        },
    )
    db.add_all([org, plan])
    await db.commit()
    return admin, owner, org, plan


@pytest.mark.asyncio
async def test_no_grant_is_pending_and_owner_cannot_self_grant():
    suffix = _suffix()
    async with worker_session_maker() as db:
        _admin, owner, org, plan = await _people(db, suffix)
        with pytest.raises(HTTPException) as pending:
            await assert_can_spend(db, owner, required_credits=0, feature_name="discover", lock_row=False)
        assert pending.value.detail["code"] == "access_pending_approval"
        with pytest.raises(HTTPException) as denied:
            await grant_organization_access(
                db, owner, org.id, plan.id, {"discover": True},
            )
        assert denied.value.status_code == 403
        assert denied.value.detail["code"] == "self_grant_denied"


@pytest.mark.asyncio
async def test_request_approval_enables_only_granted_flags_and_revoke_keeps_the_org():
    suffix = _suffix()
    async with worker_session_maker() as db:
        admin, owner, org, plan = await _people(db, suffix)
        request = await submit_access_request(db, owner, org.id, ["discover", "intelligence"], "Need search")
        assert request["status"] == "pending"
        approved = await approve_access_request(
            db, admin, request["id"], plan.id, {"discover": True, "intelligence": False},
        )
        assert approved["status"] == "approved"
        await assert_can_spend(db, owner, required_credits=0, feature_name="discover", lock_row=False)
        with pytest.raises(HTTPException) as blocked:
            await assert_can_spend(db, owner, required_credits=0, feature_name="intelligence", lock_row=False)
        assert blocked.value.detail["code"] == "feature_disabled"
        revoked = await revoke_organization_access(db, admin, org.id, "stop")
        assert revoked["data_retained"] is True
        still = await db.get(Organization, org.id)
        assert still is not None
        with pytest.raises(HTTPException) as after:
            await assert_can_spend(db, owner, required_credits=0, feature_name="discover", lock_row=False)
        assert after.value.detail["code"] == "access_revoked"


@pytest.mark.asyncio
async def test_expired_grant_blocks_spend():
    suffix = _suffix()
    async with worker_session_maker() as db:
        admin, owner, org, plan = await _people(db, suffix)
        await grant_organization_access(
            db,
            admin,
            org.id,
            plan.id,
            {"discover": True},
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        with pytest.raises(HTTPException) as exc:
            await assert_can_spend(db, owner, required_credits=0, feature_name="discover", lock_row=False)
        assert exc.value.detail["code"] == "access_expired"


@pytest.mark.asyncio
async def test_scout_worker_rechecks_entitlement_before_running():
    suffix = _suffix()
    async with worker_session_maker() as db:
        _admin, owner, org, _plan = await _people(db, suffix)
        job = ScoutJob(
            id=f"job_{suffix}",
            org_id=org.id,
            user_id=owner.id,
            status="queued",
            platforms=["github"],
            handles=["example"],
        )
        db.add(job)
        await db.commit()
        job_id = job.id
    await run_scout_job_worker(job_id)
    async with worker_session_maker() as db:
        job = await db.get(ScoutJob, job_id)
        assert job.status == "failed"
        assert "pending approval" in (job.error_msg or "").lower()


@pytest.mark.asyncio
async def test_leadgen_and_maps_workers_recheck_entitlement_before_running():
    suffix = _suffix()
    async with worker_session_maker() as db:
        _admin, owner, org, _plan = await _people(db, suffix)
        lead = LeadGenJob(id=f"lg_{suffix}", org_id=org.id, user_id=owner.id, status="queued", brief={}, seeds=[])
        maps = ScoutMapsJob(id=f"mp_{suffix}", org_id=org.id, user_id=owner.id, status="queued", keyword="clinics", city="Cairo")
        db.add_all([lead, maps])
        await db.commit()
        lead_id, maps_id = lead.id, maps.id
    await run_leadgen_job(lead_id)
    await run_maps_scout_worker(maps_id)
    async with worker_session_maker() as db:
        lead = await db.get(LeadGenJob, lead_id)
        maps = await db.get(ScoutMapsJob, maps_id)
        assert lead.status == "failed"
        assert maps.status == "failed"
        assert "pending approval" in (lead.error_msg or "").lower()
        assert "pending approval" in (maps.error_msg or "").lower()


@pytest.mark.asyncio
async def test_reject_after_revoke_reports_rejected_and_keeps_the_org():
    suffix = _suffix()
    async with worker_session_maker() as db:
        admin, owner, org, plan = await _people(db, suffix)
        await grant_organization_access(
            db, admin, org.id, plan.id, {"discover": True},
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await revoke_organization_access(db, admin, org.id, "stop")
        revoked = await access_status_for_org(db, org.id)
        assert revoked["status"] == "revoked"
        request = await submit_access_request(db, owner, org.id, ["discover"], "again")
        pending = await access_status_for_org(db, org.id)
        assert pending["status"] == "pending"
        await reject_access_request(db, admin, request["id"], "no")
        rejected = await access_status_for_org(db, org.id)
        assert rejected["code"] == "access_rejected"
        assert await db.get(Organization, org.id) is not None
