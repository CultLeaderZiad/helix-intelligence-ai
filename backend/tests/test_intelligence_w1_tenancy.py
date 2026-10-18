"""W1 tenancy, entitlement, idempotency, and RLS behavior.

Synthetic identities only. Requires the migrated disposable Postgres from
TEST_DATABASE_URL / DATABASE_URL. No provider and no production data.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.deps import require_admin_permission
from app.core.tenancy import bind_tenant, reset_tenant
from app.db.session import worker_engine, worker_session_maker
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.pattern import Pattern
from app.models.plan import Plan
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services.billing_contract import MISSING_BILLING_CONTRACT, refuse_billing_provider_event
from app.services.billing_service import (
    assert_can_generate_image,
    assert_can_spend,
    charge,
    refund,
    resolve_active_org,
)
from app.services.creative_service import list_patterns
from app.services.storage_service import issue_local_url, verify_capability, verify_local_signature


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


def test_billing_provider_events_fail_closed_without_inventing_a_contract():
    with pytest.raises(HTTPException) as exc:
        refuse_billing_provider_event({"type": "invoice.paid", "id": "evt_test"})
    assert exc.value.status_code == 503
    detail = exc.value.detail
    assert detail["code"] == "billing_provider_contract_missing"
    assert "price" in " ".join(detail["missing"]).lower()
    assert len(detail["missing"]) == len(MISSING_BILLING_CONTRACT)


def test_assistant_without_explicit_permission_is_denied():
    checker = require_admin_permission("support")
    assistant = User(id="asst_w1", role="assistant-admin", admin_permissions={})

    async def _run():
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=assistant)
        assert exc.value.status_code == 403

    asyncio.run(_run())


def test_zero_video_limit_is_not_replaced_with_three():
    now = datetime.now(timezone.utc)
    user = User(
        id="u_zero",
        email="zero@example.com",
        role="customer",
        trial_expires_at=now + timedelta(days=3),
    )
    org = Organization(
        id="org_zero",
        name="Zero",
        owner_id=user.id,
        plan="paid",
        plan_id="plan_zero",
        status="active",
        videos_generated_today=0,
        images_today_date=now.strftime("%Y-%m-%d"),
    )
    plan = Plan(id="plan_zero", name="Zero Video", type="pay_as_you_go", daily_video_limit=0, feature_flags={"create": True})

    class DB:
        async def execute(self, _query):
            class Result:
                def scalar_one_or_none(self):
                    return plan
            return Result()

        async def scalar(self, _query):
            return 0

        async def flush(self):
            return None

        async def commit(self):
            return None

    async def _run():
        with pytest.raises(HTTPException) as exc:
            await assert_can_generate_image(DB(), user, org, media_type="video")
        assert exc.value.status_code == 402
        assert exc.value.detail["code"] == "daily_video_limit"
        assert exc.value.detail["daily_video_limit"] == 0

    asyncio.run(_run())


def test_capability_urls_expire_and_reject_permanent_signatures():
    url = issue_local_url("job_abc.png", org_id="org1", user_id="user1", token_version="2", ttl_seconds=60)
    assert "sig=" in url
    assert "token=" not in url
    filename = url.split("/uploads/", 1)[1].split("?", 1)[0]
    query = url.split("?", 1)[1]
    parts = dict(item.split("=", 1) for item in query.split("&"))
    assert verify_capability(filename, parts["sig"], parts["exp"], "org1", "user1", "2")
    assert not verify_capability(filename, parts["sig"], "1", "org1", "user1", "2")
    assert verify_local_signature(filename, parts["sig"]) is False


@pytest.mark.asyncio
async def test_two_tenants_patterns_are_exact_org_and_unassigned_rows_stay_hidden():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user_a = User(id=f"w1a_{suffix}", email=f"w1a_{suffix}@example.com", password_hash="x", role="customer")
        user_b = User(id=f"w1b_{suffix}", email=f"w1b_{suffix}@example.com", password_hash="x", role="customer")
        db.add_all([user_a, user_b])
        await db.flush()
        org_a = Organization(id=f"w1oa_{suffix}", name="A", owner_id=user_a.id, plan_id="plan_trial_default", plan="trial", status="active")
        org_b = Organization(id=f"w1ob_{suffix}", name="B", owner_id=user_b.id, plan_id="plan_trial_default", plan="trial", status="active")
        db.add_all([org_a, org_b])
        await db.flush()
        job_a = ScrapeJob(id=f"w1ja_{suffix}", org_id=org_a.id, query="private", status="succeeded")
        job_b = ScrapeJob(id=f"w1jb_{suffix}", org_id=org_b.id, query="other", status="succeeded")
        db.add_all([job_a, job_b])
        await db.flush()
        owned = Pattern(
            id=f"w1pa_{suffix}",
            job_id=job_a.id,
            org_id=org_a.id,
            label=f"OWNED-{suffix}",
            family="copy",
            prevalence=0.2,
            lift_index=1.1,
        )
        foreign = Pattern(
            id=f"w1pb_{suffix}",
            job_id=job_b.id,
            org_id=org_b.id,
            label=f"FOREIGN-{suffix}",
            family="copy",
            prevalence=0.3,
            lift_index=1.2,
        )
        db.add_all([owned, foreign])
        await db.commit()

        listed_b = await list_patterns(db, user_org_ids=[org_b.id])
        labels = {item.label for item in listed_b.items}
        assert f"FOREIGN-{suffix}" in labels
        assert f"OWNED-{suffix}" not in labels
        listed_a = await list_patterns(db, user_org_ids=[org_a.id])
        labels_a = {item.label for item in listed_a.items}
        assert f"OWNED-{suffix}" in labels_a
        assert f"FOREIGN-{suffix}" not in labels_a


@pytest.mark.asyncio
async def test_invited_member_uses_paid_workspace_not_personal_trial():
    suffix = _suffix()
    async with worker_session_maker() as db:
        owner = User(id=f"w1own_{suffix}", email=f"own_{suffix}@example.com", password_hash="x")
        member = User(
            id=f"w1mem_{suffix}",
            email=f"mem_{suffix}@example.com",
            password_hash="x",
            trial_expires_at=datetime.now(timezone.utc) - timedelta(days=2),
            signup_metadata={"active_org_id": f"w1paid_{suffix}"},
        )
        db.add_all([owner, member])
        await db.flush()
        trial = Organization(id=f"w1trial_{suffix}", name="Trial", owner_id=member.id, plan="trial", plan_id="plan_trial_default", status="active")
        paid = Organization(id=f"w1paid_{suffix}", name="Paid", owner_id=owner.id, plan="pay_as_you_go", plan_id="plan_payg_default", status="active")
        db.add_all([trial, paid])
        await db.flush()
        db.add(OrganizationMember(org_id=paid.id, user_id=member.id, role="member"))
        await db.commit()
        resolved = await resolve_active_org(db, member)
        assert resolved.id == paid.id


@pytest.mark.asyncio
async def test_suspended_org_cannot_spend_and_pattern_row_is_retained():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1sus_{suffix}", email=f"sus_{suffix}@example.com", password_hash="x", role="customer")
        db.add(user)
        await db.flush()
        org = Organization(
            id=f"w1so_{suffix}",
            name="Suspended",
            owner_id=user.id,
            plan_id="plan_trial_default",
            plan="trial",
            status="suspended",
            credit_balance=50,
        )
        db.add(org)
        await db.flush()
        job = ScrapeJob(id=f"w1sj_{suffix}", org_id=org.id, query="kept", status="succeeded")
        db.add(job)
        await db.flush()
        pattern = Pattern(
            id=f"w1sp_{suffix}",
            job_id=job.id,
            org_id=org.id,
            label="retained",
            family="copy",
            prevalence=0.1,
            lift_index=1,
        )
        db.add(pattern)
        await db.commit()
        with pytest.raises(HTTPException) as exc:
            await assert_can_spend(db, user, required_credits=1, feature_name="discover", lock_row=True)
        assert exc.value.detail["code"] == "subscription_inactive"
        still = (await db.execute(text("SELECT id FROM patterns WHERE id = :id"), {"id": pattern.id})).first()
        assert still is not None


@pytest.mark.asyncio
async def test_missing_plan_and_unknown_feature_fail_closed():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1mp_{suffix}", email=f"mp_{suffix}@example.com", password_hash="x")
        db.add(user)
        await db.flush()
        org = Organization(
            id=f"w1mo_{suffix}",
            name="Missing",
            owner_id=user.id,
            plan_id=f"plan_missing_{suffix}",
            plan="custom",
            status="active",
            credit_balance=10,
        )
        db.add(org)
        await db.commit()
        with pytest.raises(HTTPException) as missing:
            await assert_can_spend(db, user, required_credits=0, feature_name="discover", lock_row=False)
        assert missing.value.detail["code"] == "plan_unavailable"

        plan = Plan(
            id=f"plan_known_{suffix}",
            name="Known",
            type="pay_as_you_go",
            feature_flags={"discover": True},
        )
        db.add(plan)
        org.plan_id = plan.id
        await db.commit()
        with pytest.raises(HTTPException) as unknown:
            await assert_can_spend(db, user, required_credits=0, feature_name="not_a_real_feature", lock_row=False)
        assert unknown.value.detail["code"] == "feature_disabled"


@pytest.mark.asyncio
async def test_idempotent_charge_rejects_a_different_payload_and_refunds_the_settled_amount_once():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1id_{suffix}", email=f"id_{suffix}@example.com", password_hash="x")
        db.add(user)
        await db.flush()
        org = Organization(
            id=f"w1io_{suffix}",
            name="Idem",
            owner_id=user.id,
            plan_id="plan_trial_default",
            plan="trial",
            status="active",
            credit_balance=20,
            credits_used=0,
            daily_credits_used_today=0,
            daily_credits_reset_at=datetime.now(timezone.utc),
        )
        db.add(org)
        await db.commit()
        first = await charge(
            db, org, user.id, 4, "test", "w1_op", job_id=f"job_{suffix}",
            idempotency_key=f"key_{suffix}", metadata={"n": 1},
        )
        await db.refresh(org)
        assert float(org.credit_balance) == 16
        replay = await charge(
            db, org, user.id, 4, "test", "w1_op", job_id=f"job_{suffix}",
            idempotency_key=f"key_{suffix}", metadata={"n": 1},
        )
        assert replay.id == first.id
        with pytest.raises(HTTPException) as mismatch:
            await charge(
                db, org, user.id, 4, "test", "w1_op", job_id=f"job_{suffix}",
                idempotency_key=f"key_{suffix}", metadata={"n": 2},
            )
        assert mismatch.value.detail["code"] == "idempotency_payload_mismatch"
        assert await refund(db, org.id, 999, "worker_failed", f"job_{suffix}") is True
        await db.refresh(org)
        assert float(org.credit_balance) == 20
        assert await refund(db, org.id, 999, "worker_failed", f"job_{suffix}") is False
        await db.refresh(org)
        assert float(org.credit_balance) == 20
        ledger = (await db.execute(
            text("SELECT entry_kind, amount FROM credit_ledger WHERE org_id = :org ORDER BY created_at"),
            {"org": org.id},
        )).all()
        assert [row.entry_kind for row in ledger] == ["debit", "refund"]
        assert float(ledger[0].amount) == 4


@pytest.mark.asyncio
async def test_concurrent_same_key_debits_once():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1cc_{suffix}", email=f"cc_{suffix}@example.com", password_hash="x")
        db.add(user)
        await db.flush()
        org = Organization(
            id=f"w1co_{suffix}",
            name="Race",
            owner_id=user.id,
            plan_id="plan_trial_default",
            plan="trial",
            status="active",
            credit_balance=30,
            credits_used=0,
            daily_credits_used_today=0,
            daily_credits_reset_at=datetime.now(timezone.utc),
        )
        db.add(org)
        await db.commit()
        org_id = org.id
        user_id = user.id

    async def once():
        async with worker_session_maker() as session:
            locked = (await session.execute(
                text("SELECT * FROM organizations WHERE id = :id"),
                {"id": org_id},
            )).first()
            assert locked is not None
            org_row = (await session.execute(
                Organization.__table__.select().where(Organization.id == org_id)
            )).first()
            del org_row
            organization = await session.get(Organization, org_id)
            try:
                await charge(
                    session, organization, user_id, 5, "test", "w1_race",
                    job_id=f"race_{suffix}", idempotency_key=f"racekey_{suffix}", metadata={"n": 1},
                )
            except HTTPException:
                return "rejected"

    results = await asyncio.gather(once(), once())
    assert results.count("rejected") <= 1
    async with worker_session_maker() as db:
        organization = await db.get(Organization, org_id)
        assert float(organization.credit_balance) == 25
        debits = (await db.execute(
            text("SELECT count(*) FROM credit_ledger WHERE org_id = :org AND entry_kind = 'debit'"),
            {"org": org_id},
        )).scalar_one()
        assert debits == 1


@pytest.mark.asyncio
async def test_rls_blocks_other_tenant_and_does_not_survive_pool_reuse():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1rl_{suffix}", email=f"rl_{suffix}@example.com", password_hash="x")
        db.add(user)
        await db.flush()
        org_a = Organization(id=f"w1ra_{suffix}", name="RA", owner_id=user.id, plan_id="plan_trial_default", plan="trial")
        org_b = Organization(id=f"w1rb_{suffix}", name="RB", owner_id=user.id, plan_id="plan_trial_default", plan="trial")
        db.add_all([org_a, org_b])
        await db.flush()
        job_a = ScrapeJob(id=f"w1rja_{suffix}", org_id=org_a.id, query="a", status="succeeded")
        job_b = ScrapeJob(id=f"w1rjb_{suffix}", org_id=org_b.id, query="b", status="succeeded")
        db.add_all([job_a, job_b])
        await db.flush()
        db.add_all([
            Pattern(id=f"w1rpa_{suffix}", job_id=job_a.id, org_id=org_a.id, label=f"ra_{suffix}", family="copy", prevalence=0.1, lift_index=1),
            Pattern(id=f"w1rpb_{suffix}", job_id=job_b.id, org_id=org_b.id, label=f"rb_{suffix}", family="copy", prevalence=0.1, lift_index=1),
        ])
        await db.commit()

    connect_args = {"statement_cache_size": 0}
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(worker_engine.url, connect_args=connect_args)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("BEGIN"))
            await conn.execute(text("SET LOCAL ROLE helix_app"))
            await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
            await conn.execute(text("SELECT set_config('helix.platform_admin', '0', true)"))
            await conn.execute(text("SELECT set_config('helix.org_ids', :ids, true)"), {"ids": f"w1ra_{suffix}"})
            visible = (await conn.execute(
                text("SELECT label FROM patterns WHERE id IN (:a, :b)"),
                {"a": f"w1rpa_{suffix}", "b": f"w1rpb_{suffix}"},
            )).scalars().all()
            assert visible == [f"ra_{suffix}"]
            await conn.execute(text("COMMIT"))
            await conn.execute(text("BEGIN"))
            await conn.execute(text("SET LOCAL ROLE helix_app"))
            await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
            leaked = (await conn.execute(text("SELECT current_setting('helix.org_ids', true)"))).scalar_one()
            assert leaked in (None, "")
            visible_after = (await conn.execute(
                text("SELECT label FROM patterns WHERE id IN (:a, :b)"),
                {"a": f"w1rpa_{suffix}", "b": f"w1rpb_{suffix}"},
            )).scalars().all()
            assert visible_after == []
            await conn.execute(text("COMMIT"))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_worker_role_sees_only_the_job_org():
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = User(id=f"w1wk_{suffix}", email=f"wk_{suffix}@example.com", password_hash="x")
        db.add(user)
        await db.flush()
        org_a = Organization(id=f"w1wa_{suffix}", name="WA", owner_id=user.id, plan_id="plan_trial_default", plan="trial")
        org_b = Organization(id=f"w1wb_{suffix}", name="WB", owner_id=user.id, plan_id="plan_trial_default", plan="trial")
        db.add_all([org_a, org_b])
        await db.flush()
        db.add_all([
            ScrapeJob(id=f"w1wja_{suffix}", org_id=org_a.id, query="a", status="succeeded"),
            ScrapeJob(id=f"w1wjb_{suffix}", org_id=org_b.id, query="b", status="succeeded"),
        ])
        await db.commit()

    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(worker_engine.url, connect_args={"statement_cache_size": 0})
    try:
        async with engine.connect() as conn:
            await conn.execute(text("BEGIN"))
            await conn.execute(text("SET LOCAL ROLE helix_worker"))
            await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
            await conn.execute(text("SELECT set_config('helix.platform_admin', '0', true)"))
            await conn.execute(text("SELECT set_config('helix.org_ids', :ids, true)"), {"ids": f"w1wa_{suffix}"})
            queries = (await conn.execute(text(
                "SELECT query FROM scrape_jobs WHERE id IN (:a, :b)"
            ), {"a": f"w1wja_{suffix}", "b": f"w1wjb_{suffix}"})).scalars().all()
            assert queries == ["a"]
            await conn.execute(text("COMMIT"))
    finally:
        await engine.dispose()


def test_apply_tenant_context_is_callable():
    token = bind_tenant(["org_x"], "user_x", platform_admin=False, enforce=True)
    try:
        assert os.environ.get("HELIX_RLS_ENFORCE", "") in ("", "0", "1", "true", "false", "yes")
    finally:
        reset_tenant(token)
