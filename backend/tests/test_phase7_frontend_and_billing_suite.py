import pytest
import os
import sys
import uuid
import datetime
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from jose import jwt

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db.session import worker_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative


@pytest.mark.asyncio
async def test_f79_honest_subscription_lifecycle_and_no_fake_renewal():
    """F79: Paid & pay-as-you-go plans display honest lifecycle metadata without false Monthly renewal."""
    from app.services import billing_service

    async with worker_session_maker() as db:
        # Create test plans
        plan_payg = Plan(
            id=f"plan_payg_{uuid.uuid4().hex[:8]}",
            name="Pay As You Go",
            type="pay_as_you_go",
            credit_allowance=100,
            daily_credit_limit=50.0,
            price_per_credit=0.10
        )
        plan_starter = Plan(
            id=f"plan_starter_{uuid.uuid4().hex[:8]}",
            name="Starter Pro",
            type="pro",
            credit_allowance=500,
            daily_credit_limit=100.0,
            price_per_credit=0.08
        )
        db.add_all([plan_payg, plan_starter])
        await db.commit()

        # 1. Test pay-as-you-go user
        uid_payg = f"usr_payg_{uuid.uuid4().hex[:8]}"
        oid_payg = f"org_payg_{uuid.uuid4().hex[:8]}"
        user_payg = User(
            id=uid_payg,
            email=f"{uid_payg}@example.com",
            password_hash="hash"
        )
        db.add(user_payg)
        await db.flush()

        org_payg = Organization(
            id=oid_payg,
            name="PayG Org",
            owner_id=user_payg.id,
            plan_id=plan_payg.id,
            credit_balance=50.0
        )
        db.add(org_payg)
        await db.commit()

        summary_payg = await billing_service.get_org_billing_summary(db, user_payg)
        assert summary_payg["plan_type"] == "pay_as_you_go"
        assert summary_payg["subscription_lifecycle"] == "metered"
        assert summary_payg["renews_at"] is None

        # 2. Test starter/pro user
        uid_pro = f"usr_pro_{uuid.uuid4().hex[:8]}"
        oid_pro = f"org_pro_{uuid.uuid4().hex[:8]}"
        user_pro = User(
            id=uid_pro,
            email=f"{uid_pro}@example.com",
            password_hash="hash"
        )
        db.add(user_pro)
        await db.flush()

        org_pro = Organization(
            id=oid_pro,
            name="Pro Org",
            owner_id=user_pro.id,
            plan_id=plan_starter.id,
            credit_balance=500.0
        )
        db.add(org_pro)
        await db.commit()

        summary_pro = await billing_service.get_org_billing_summary(db, user_pro)
        assert summary_pro["plan_type"] == "pro"
        assert summary_pro["subscription_lifecycle"] == "admin_allocated"
        assert summary_pro["renews_at"] is None


@pytest.mark.asyncio
async def test_f51_impersonation_token_identity():
    """F51: Admin impersonation returns a token scoped strictly to the impersonated user."""
    from app.services import admin_service

    async with worker_session_maker() as db:
        uid_admin = f"usr_adm_{uuid.uuid4().hex[:8]}"
        uid_target = f"usr_tgt_{uuid.uuid4().hex[:8]}"
        admin_user = User(
            id=uid_admin,
            email=f"{uid_admin}@example.com",
            password_hash="hash",
            role="admin"
        )
        target_user = User(
            id=uid_target,
            email=f"{uid_target}@example.com",
            password_hash="hash",
            role="member"
        )
        db.add(admin_user)
        db.add(target_user)
        await db.flush()

        admin_org = Organization(
            id=f"org_adm_{uuid.uuid4().hex[:8]}",
            name="Admin Org",
            owner_id=admin_user.id
        )
        target_org = Organization(
            id=f"org_tgt_{uuid.uuid4().hex[:8]}",
            name="Target Org",
            owner_id=target_user.id
        )
        db.add(admin_org)
        db.add(target_org)
        await db.commit()

        # Admin impersonates target user
        result = await admin_service.impersonate_user(db, target_user.id, admin_user)
        token = getattr(result, "access_token", None) or result.get("access_token")
        assert token is not None

        # Decode token and verify subject is the TARGET user, not the admin
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_aud": False})
        assert payload is not None
        assert payload.get("sub") == str(target_user.id)


@pytest.mark.asyncio
async def test_f44_playbook_compilation_preserves_job_id():
    """F44: Compiling a playbook with job_id associates the job's creatives and brand."""
    from app.services import playbook_service

    async with worker_session_maker() as db:
        uid = f"usr_pb_{uuid.uuid4().hex[:8]}"
        oid = f"org_pb_{uuid.uuid4().hex[:8]}"
        user = User(
            id=uid,
            email=f"{uid}@example.com",
            password_hash="hash"
        )
        db.add(user)
        await db.flush()

        org = Organization(
            id=oid,
            name="Playbook Org",
            owner_id=user.id
        )
        db.add(org)
        await db.flush()

        # Create scrape job and creative
        jid = f"job_pb_{uuid.uuid4().hex[:8]}"
        job = ScrapeJob(
            id=jid,
            org_id=org.id,
            query="Athletic Greens",
            status="succeeded"
        )
        db.add(job)
        await db.flush()

        cid = f"cr_pb_{uuid.uuid4().hex[:8]}"
        creative = Creative(
            id=cid,
            job_id=job.id,
            brand_id="brand_ag",
            brand_name="Athletic Greens",
            headline="Daily Nutrition Made Simple",
            format="video",
            days_active=18,
            platform="meta"
        )
        db.add(creative)
        await db.commit()

        # Compile playbook explicitly passing job_id
        playbook = await playbook_service.compile_playbook(
            db=db,
            user=user,
            brand_name="Athletic Greens",
            query="Athletic Greens",
            job_id=str(job.id)
        )
        assert playbook is not None
        assert playbook.brand_name == "Athletic Greens"
        assert playbook.public_id is not None
        assert len(playbook.creatives) > 0


@pytest.mark.asyncio
async def test_f57_leadgen_worker_offline_structured_error():
    """F57: Structured worker_offline error returned with status 503 and proper code."""
    from app.api.routers import leadgen
    from app.schemas.leadgen import CreateLeadGenJobRequest, LeadGenBrief, LeadGenSeeds
    from fastapi import HTTPException

    req = CreateLeadGenJobRequest(
        brief=LeadGenBrief(icp="B2B SaaS Founders", max_pages=5, max_leads=10),
        seeds=LeadGenSeeds(urls=["https://example.com"])
    )

    async with worker_session_maker() as db:
        uid = f"usr_off_{uuid.uuid4().hex[:8]}"
        oid = f"org_off_{uuid.uuid4().hex[:8]}"
        user = User(
            id=uid,
            email=f"{uid}@example.com",
            password_hash="hash"
        )
        db.add(user)
        await db.flush()
        org = Organization(
            id=oid,
            name="Leadgen Org",
            owner_id=user.id
        )
        db.add(org)
        await db.commit()

        # When worker is not available, router must raise HTTPException 503 with structured worker_offline code
        with patch("app.api.routers.leadgen._is_worker_available", return_value=False):
            try:
                await leadgen.create_leadgen_job(
                    req=req,
                    db=db,
                    current_user=user,
                    idempotency_key=None
                )
                assert False, "Should have raised HTTPException 503"
            except HTTPException as exc:
                assert exc.status_code == 503
                detail = exc.detail
                assert isinstance(detail, dict)
                assert detail.get("code") == "worker_offline"
                assert "worker is offline" in detail.get("message", "").lower()
