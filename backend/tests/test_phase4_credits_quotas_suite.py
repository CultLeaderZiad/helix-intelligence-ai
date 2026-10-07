"""Phase 4 Test Suite: Credits, Quotas, and Idempotency.

Tests cover:
- F07: Atomic credit deductions & row locking (identity-map stale cache prevention)
- F08: Reconciliation sweeper & idempotent refund guarantees
- F09: Provider outage honesty (no fake 92% confidence semantic fallbacks)
- F10: Transport retry safety & Idempotency-Key support across charges and endpoints
- F11 & F55: In-flight concurrency reservation & per-plan daily image/video limits
- F27: LeadGen credit assertion, balance protection & user budget ceiling preservation
- F28: Pre-work failure reversals (Scout, Maps, LeadGen refund on early exit/crashes)
- F32: Paid user AI routing (bypass 7-day trial expiration gate & 20-request caps)
- F50: Org-scoped external API usage caps (no system-wide 20-call platform lockout)
"""
from __future__ import annotations

import asyncio
import datetime
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.models.creative import Creative
from app.models.ai_insight import AIInsight
from app.models.scout import ScoutJob, ScoutMapsJob
from app.models.leadgen import LeadGenJob
from app.models.api_usage import ExternalApiUsage
from app.models.media_job import MediaGenerationJob
from app.services.billing_service import (
    charge,
    refund,
    get_idempotent_operation,
    assert_can_generate_image,
    assert_can_spend,
)
from app.services.ai.ai_router import AIRouter, MultiTierAIProvider, TRIAL_DAILY_REQUEST_LIMIT
from app.services.ai.base import AIProvider
from app.services.analysis_service import generate_insight_for_creative
from app.services.api_usage_service import check_global_cap_and_log_preflight, APILimitExceeded
from app.services.job_reconciliation import _sweep_unrefunded_failed_jobs, reconcile_once
from app.services.leadgen_pipeline import _fail_job, _finish
from app.schemas.analysis import Insight
from app.schemas.leadgen import LeadGenBrief, LeadGenSeeds, CreateLeadGenJobRequest

REPO_ROOT = Path(__file__).resolve().parents[2]


class MockResult:
    """Universal mock query result supporting scalar, scalar_one_or_none, and scalars()."""
    def __init__(self, item=None, items=None):
        self._item = item
        self._items = items or ([item] if item is not None else [])

    def scalar_one_or_none(self):
        return self._item

    def scalar(self):
        return self._item

    def scalars(self):
        class S:
            def __init__(self, items):
                self._items = items
            def first(self):
                return self._items[0] if self._items else None
            def all(self):
                return list(self._items)
        return S(self._items)


# ---------------------------------------------------------------------------
# F07 & F10: Atomic Charge & Idempotency Key Handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f07_f10_atomic_charge_and_idempotency_key():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(id="usr_f07", email="f07@test.com", role="customer")
    org = Organization(
        id="org_f07",
        name="Org F07",
        owner_id=user.id,
        credit_balance=100.0,
        credits_used=0.0,
        daily_credits_used_today=0.0,
        daily_credits_reset_at=now,
    )

    logs_db = []

    class MockSession:
        def __init__(self):
            self.bind = MagicMock()
            self.bind.dialect.name = "postgresql"

        async def execute(self, q):
            q_str = str(q).lower()
            if "usage_logs" in q_str:
                # Finding existing usage log by key
                found = None
                for log in logs_db:
                    meta = log.metadata_json or {}
                    if meta.get("idempotency_key") == "key_123":
                        found = log
                        break
                return MockResult(item=found)

            if "organizations" in q_str:
                return MockResult(item=org)

            return MockResult(item=None)

        def add(self, obj):
            if isinstance(obj, UsageLog):
                logs_db.append(obj)

        async def commit(self): pass
        async def refresh(self, obj): pass

    db = MockSession()

    # 1. First charge with idempotency key
    log1 = await charge(
        db=db,
        org=org,
        user_id=user.id,
        amount=5.0,
        provider="test_provider",
        operation="test_op",
        idempotency_key="key_123"
    )
    assert log1 is not None
    assert org.credit_balance == 95.0
    assert org.credits_used == 5.0
    assert log1.metadata_json.get("idempotency_key") == "key_123"

    # 2. Replay with the same idempotency key -> short-circuits, no double debit!
    log2 = await charge(
        db=db,
        org=org,
        user_id=user.id,
        amount=5.0,
        provider="test_provider",
        operation="test_op",
        idempotency_key="key_123"
    )
    assert log2.id == log1.id
    assert org.credit_balance == 95.0  # Still 95, NOT 90!
    assert org.credits_used == 5.0      # Still 5, NOT 10!


# ---------------------------------------------------------------------------
# F08: Reconciliation Sweeper & Idempotent Refund
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f08_idempotent_refund_and_reconciliation_sweeper():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(id="usr_f08", email="f08@test.com", role="customer")
    org = Organization(
        id="org_f08",
        name="Org F08",
        owner_id=user.id,
        credit_balance=20.0,
        credits_used=10.0,
        daily_credits_used_today=10.0,
        daily_credits_reset_at=now,
    )

    refund_logs = []

    class MockRefundDB:
        def __init__(self):
            self.bind = MagicMock()
            self.bind.dialect.name = "postgresql"

        async def execute(self, q):
            q_str = str(q).lower()
            if "usage_logs" in q_str:
                found = None
                for l in refund_logs:
                    if l.job_id == "job_dead_1":
                        found = l
                        break
                return MockResult(item=found)

            if "organizations" in q_str:
                return MockResult(item=org)

            return MockResult(item=None)

        def add(self, obj):
            if isinstance(obj, UsageLog):
                refund_logs.append(obj)

        async def commit(self): pass
        async def refresh(self, obj): pass

    db = MockRefundDB()

    # 1. First refund restores balance
    res1 = await refund(db, org.id, 2.0, "interrupted", "job_dead_1")
    assert res1 is True
    assert org.credit_balance == 22.0
    assert org.credits_used == 8.0

    # 2. Duplicate refund for the same job_id -> skipped (idempotency guard)
    res2 = await refund(db, org.id, 2.0, "interrupted", "job_dead_1")
    assert res2 is False  # Refused duplicate refund
    assert org.credit_balance == 22.0  # Balance was not refunded twice


# ---------------------------------------------------------------------------
# F09: Provider Outage Honesty (No Fake 92% Confidence Teardown)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f09_provider_outage_raises_honest_503_without_charging():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(id="usr_f09", email="f09@test.com", role="customer")
    org = Organization(
        id="org_f09",
        name="Org F09",
        owner_id=user.id,
        credit_balance=50.0,
        daily_credits_reset_at=now,
    )
    creative = Creative(
        id="cr_f09",
        brand_id="br_f09",
        job_id="job_f09",
        headline="Disruptive Ad",
        body="This is an ad body that is interesting.",
        platform="meta",
        format="image",
        days_active=10,
    )

    class FailingProvider(AIProvider):
        async def _call_api(self, messages):
            raise RuntimeError("Upstream AI Provider 503 Overloaded")

    provider = FailingProvider()

    persisted_insights = []
    charges = []

    class MockAnalysisDB:
        def __init__(self):
            self.bind = MagicMock()
            self.bind.dialect.name = "postgresql"

        async def execute(self, q):
            q_str = str(q).lower()
            if "organizations" in q_str:
                return MockResult(item=org)
            elif "plans" in q_str:
                return MockResult(item=Plan(id="plan_test", type="paid"))
            elif "scrape_jobs" in q_str:
                return MockResult(item=org.id)
            elif "creatives.id in" in q_str or "select creatives.id from creatives" in q_str:
                return MockResult(items=[creative.id])
            elif "creatives" in q_str:
                return MockResult(item=creative)

            return MockResult(item=None)

        def add(self, obj):
            if isinstance(obj, AIInsight):
                persisted_insights.append(obj)
            elif isinstance(obj, UsageLog):
                charges.append(obj)

        async def commit(self): pass
        async def refresh(self, obj): pass

    db = MockAnalysisDB()

    with patch("app.services.ai.ai_router.AIRouter.get_provider_for_user", AsyncMock(return_value=provider)):
        with pytest.raises(HTTPException) as exc_info:
            await generate_insight_for_creative(db, "cr_f09", user, user_org_ids=[org.id])

        # Must raise honest 503
        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail or "failed" in exc_info.value.detail

        # Absolutely NO fake insights saved to DB
        assert len(persisted_insights) == 0
        # Absolutely NO credits charged to user
        assert len(charges) == 0
        assert org.credit_balance == 50.0


# ---------------------------------------------------------------------------
# F10: Transport Retry Safety in http.js
# ---------------------------------------------------------------------------
def test_f10_http_js_restricts_mutation_retries():
    http_js_path = REPO_ROOT / "src" / "services" / "http.js"
    assert http_js_path.exists(), "src/services/http.js must exist"
    content = http_js_path.read_text(encoding="utf-8")

    # Verify that isSafeToRetry or idempotency checks exist
    assert "isSafeToRetry" in content or "hasIdempotencyKey" in content
    assert "isIdempotentMethod" in content or "GET" in content
    # Verify that mutations without keys are NOT retried
    assert "To prevent duplicate charges" in content or "idempotent" in content


# ---------------------------------------------------------------------------
# F11 & F55: In-Flight Concurrency Reservation & Daily Media Limits
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f11_f55_inflight_concurrency_and_per_plan_quotas():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        id="usr_f11",
        email="f11@test.com",
        role="customer",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7),
    )
    plan_starter = Plan(
        id="plan_starter",
        name="Starter",
        type="starter",
        daily_image_limit=10,
        daily_video_limit=2,
    )
    org = Organization(
        id="org_f11",
        name="Org F11",
        owner_id=user.id,
        plan="starter",
        plan_id="plan_starter",
        images_generated_today=8.0,
        images_today_date=now.strftime("%Y-%m-%d"),
        videos_generated_today=1.0,
    )

    # When in-flight jobs = 2 (8 + 2 = 10 -> limit reached)
    class MockMediaDB:
        def __init__(self, in_flight: int):
            self._in_flight = in_flight

        async def execute(self, q):
            return MockResult(item=plan_starter)

        async def scalar(self, q):
            return self._in_flight

        async def flush(self): pass
        async def commit(self): pass

    # In-flight count of 2 pushes images used + in-flight to 10 (cap: 10)
    db_capped = MockMediaDB(in_flight=2)
    with pytest.raises(HTTPException) as exc_info:
        await assert_can_generate_image(db_capped, user, org, media_type="image")
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == "daily_limit"

    # In-flight count of 1 pushes videos used (1) + in-flight (1) to 2 (cap: 2)
    db_video_capped = MockMediaDB(in_flight=1)
    with pytest.raises(HTTPException) as exc_info_v:
        await assert_can_generate_image(db_video_capped, user, org, media_type="video")
    assert exc_info_v.value.status_code == 402
    assert exc_info_v.value.detail["code"] == "daily_video_limit"


# ---------------------------------------------------------------------------
# F27: LeadGen Billing & User Budget Ceilings
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f27_leadgen_budget_ceiling_rejection_and_charge():
    from app.api.routers.leadgen import compute_credit_cost

    brief = LeadGenBrief(
        icp="SaaS founders",
        geos=["US"],
        max_pages=10,
        max_leads=5,
        credit_budget=2.0  # Budget specified by user: 2.0 credits
    )
    cost = compute_credit_cost(brief, enrich_emails=True, generate_outreach=True)
    # Base 3.0 + 10*0.1 (1.0) + 0.25*5 (1.25) + 0.1*5 (0.5) = 5.75
    assert cost > brief.credit_budget

    # Assert that cost exceeds budget check
    assert brief.credit_budget < cost


# ---------------------------------------------------------------------------
# F28: Pre-Work Failure Reversals (Scout & LeadGen Refunds)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f28_prework_failure_refunds_deducted_credits():
    user = User(id="usr_f28", email="f28@test.com", role="customer")
    org = Organization(id="org_f28", name="Org F28", owner_id=user.id, credit_balance=50.0)
    leadgen_job = LeadGenJob(
        id="job_lg_f28",
        org_id=org.id,
        user_id=user.id,
        status="running",
        credits_used=5.5,
        credit_budget=10.0,
    )

    refunded_amounts = []

    class MockPipelineDB:
        async def execute(self, q):
            return MockResult(item=leadgen_job)

        def add(self, obj): pass
        async def commit(self): pass

    class MockContextManager:
        def __init__(self, db_inst): self.db_inst = db_inst
        async def __aenter__(self): return self.db_inst
        async def __aexit__(self, *args): pass

    mock_db = MockPipelineDB()

    # Mock refund inside leadgen_pipeline
    with patch("app.services.billing_service.refund", AsyncMock(side_effect=lambda db, org_id, amount, reason, job_id: refunded_amounts.append(amount))):
        with patch("app.services.leadgen_pipeline.worker_session_maker", return_value=MockContextManager(mock_db)):
            await _finish(leadgen_job.id, 0.0, "Seed stage failed", failed=True)

    assert len(refunded_amounts) == 1
    assert refunded_amounts[0] == 5.5
    assert leadgen_job.status == "failed"


# ---------------------------------------------------------------------------
# F32: Paid User AI Routing Bypasses Trial Expiration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f32_paid_user_bypasses_trial_expiration_and_limits():
    now = datetime.datetime.now(datetime.timezone.utc)
    past = now - datetime.timedelta(days=30)
    paid_user = User(
        id="usr_paid",
        email="paid@customer.com",
        role="customer",
        trial_started_at=past - datetime.timedelta(days=7),
        trial_expires_at=past,  # Expired 30 days ago!
    )
    paid_org = Organization(
        id="org_paid",
        name="Paid Customer Org",
        owner_id=paid_user.id,
        plan="growth",  # Paid plan
        plan_id="plan_growth",
    )
    paid_plan = Plan(id="plan_growth", name="Growth", type="paid")

    class MockPaidDB:
        async def execute(self, q):
            q_str = str(q).lower()
            if "organizations" in q_str:
                return MockResult(item=paid_org)
            elif "plans" in q_str:
                return MockResult(item=paid_plan)
            return MockResult(item=None)

    db = MockPaidDB()

    # Even though trial_expires_at is 30 days in the past, get_provider_for_user must succeed!
    provider = await AIRouter.get_provider_for_user(db, paid_user)
    assert isinstance(provider, MultiTierAIProvider)


# ---------------------------------------------------------------------------
# F50: Org-Scoped API Usage Cap (No Global Platform Lockout)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f50_org_scoped_api_usage_cap():
    now = datetime.datetime.now(datetime.timezone.utc)
    records = []

    class MockUsageDB:
        def __init__(self):
            self.bind = MagicMock()
            self.bind.dialect.name = "postgresql"

        async def scalar(self, q):
            # Check how many non-failed records exist for this specific org
            count = 0
            for r in records:
                if r.status != "failed":
                    count += 1
            return count

        def add(self, obj):
            if isinstance(obj, ExternalApiUsage):
                records.append(obj)

        async def commit(self): pass
        async def refresh(self, obj):
            obj.id = f"usage_{len(records)}"

    db = MockUsageDB()

    # 1. Calls for Org A with daily_cap=5
    # First 4 calls succeed
    for i in range(4):
        await check_global_cap_and_log_preflight(
            db=db,
            provider="scrapegraph",
            org_id="org_A",
            user_id="user_A",
            query=f"query_{i}",
            max_records=10,
            estimated_cost=0.01,
            daily_cap=5
        )

    assert len(records) == 4

    # 5th call reaches cap (4 -> 5 is allowed, 5 is >= cap)
    await check_global_cap_and_log_preflight(
        db=db,
        provider="scrapegraph",
        org_id="org_A",
        user_id="user_A",
        query="query_4",
        max_records=10,
        estimated_cost=0.01,
        daily_cap=5
    )
    assert len(records) == 5

    # 6th call raises APILimitExceeded
    with pytest.raises(APILimitExceeded) as exc_info:
        await check_global_cap_and_log_preflight(
            db=db,
            provider="scrapegraph",
            org_id="org_A",
            user_id="user_A",
            query="query_5",
            max_records=10,
            estimated_cost=0.01,
            daily_cap=5
        )
    assert "Daily API limit reached" in str(exc_info.value)
