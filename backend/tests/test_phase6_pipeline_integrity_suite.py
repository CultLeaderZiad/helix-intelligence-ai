import pytest
import os
import sys
import uuid
import datetime
from unittest.mock import patch, AsyncMock, MagicMock, create_autospec
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import worker_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.access_grant import OrganizationAccessGrant


async def _grant_workspace(db, org, user, flags):
    db.add(OrganizationAccessGrant(
        org_id=org.id,
        plan_id=org.plan_id or "plan_trial_default",
        feature_flags=flags,
        granted_by_user_id=user.id,
    ))
    await db.commit()


_PHASE6_FLAGS = {
    "discover": True,
    "intelligence": True,
    "create": True,
    "swipe_files": True,
    "scout": False,
    "leadgen": False,
    "monitors": False,
}


@pytest.mark.asyncio
async def test_storage_service_save_file_and_r2_validation(monkeypatch, tmp_path):
    """F34 & F49: Test save_file writes and R2 validation rules."""
    from app.services import storage_service
    from urllib.parse import parse_qs, urlsplit

    monkeypatch.setattr(storage_service, "UPLOAD_DIR", str(tmp_path))

    # 1. Empty data should raise ValueError
    with pytest.raises(ValueError):
        await storage_service.save_file(b"", "empty.png")

    # 2. Local storage write
    data = b"fake-avatar-bytes"
    url = await storage_service.save_file(data, "avatar.png", content_type="image/png")
    assert url is not None
    assert "avatar_" in url
    assert url.startswith("/uploads/") and "sig=" not in url
    assert (tmp_path / urlsplit(url).path.rsplit("/", 1)[-1]).read_bytes() == data
    signed = storage_service.resolve_stored_url(
        url, org_id="storage-test-org", user_id="storage-test-user", token_version="1",
    )
    parts = urlsplit(signed)
    query = {key: values[0] for key, values in parse_qs(parts.query).items()}
    assert query["org"] == "storage-test-org" and query["uid"] == "storage-test-user"
    assert storage_service.verify_capability(
        parts.path.rsplit("/", 1)[-1], query["sig"], query["exp"],
        query["org"], query["uid"], query["ver"],
    )

    # 3. Partial R2 configuration must raise RuntimeError (F49)
    with patch.object(storage_service.settings, "R2_ACCOUNT_ID", "acc_123"), \
         patch.object(storage_service.settings, "R2_ACCESS_KEY_ID", None):
        with pytest.raises(RuntimeError, match="partially configured"):
            storage_service.r2_enabled()

    # 4. Production without complete R2 must raise RuntimeError (F49)
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}), \
         patch.object(storage_service.settings, "R2_ACCOUNT_ID", None), \
         patch.object(storage_service.settings, "R2_ACCESS_KEY_ID", None):
        with pytest.raises(RuntimeError, match="required in production"):
            storage_service.r2_enabled()








@pytest.mark.asyncio
async def test_custom_swipe_reference_integrity():
    """F33: Custom swipe references link parent ScrapeJob, set brand_id, and have impressions_est=None."""
    from app.services.creative_service import create_custom_swipe_reference

    async with worker_session_maker() as db:
        test_uid = f"usr_sw_{uuid.uuid4().hex[:8]}"
        test_oid = f"org_sw_{uuid.uuid4().hex[:8]}"
        u = User(id=test_uid, email=f"{test_uid}@example.com", password_hash="pw", role="member")
        o = Organization(id=test_oid, name="Swipe Org", owner_id=test_uid, plan="pro", credit_balance=50.0)
        db.add(u)
        await db.flush()
        db.add(o)
        await db.commit()
        await _grant_workspace(db, o, u, _PHASE6_FLAGS)

        res = await create_custom_swipe_reference(
            db=db,
            user=u,
            data={
                "url": "https://example.com/ad/123",
                "headline": "Game Changing Product",
                "body": "Check this custom ad out",
                "platform": "web"
            }
        )
        assert res["success"] is True
        c_id = res["creative_id"]

        # Verify Creative row
        c = (await db.execute(select(Creative).where(Creative.id == c_id))).scalar_one()
        assert c.brand_id is not None
        assert c.job_id == f"custom_job_{test_oid}"
        assert c.impressions_est is None  # Honest metric, not fake 10000
        assert c.is_estimated is False

        # Verify parent ScrapeJob was created
        sj = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == f"custom_job_{test_oid}"))).scalar_one_or_none()
        assert sj is not None
        assert sj.org_id == test_oid


@pytest.mark.asyncio
async def test_support_ticket_batching_and_pagination():
    """F37 & F64: Support tickets batch queries to prevent N+1 and support pagination."""
    from app.services.support_service import create_ticket, add_reply, list_user_tickets, get_ticket_details, list_admin_tickets

    async with worker_session_maker() as db:
        admin_uid = f"adm_{uuid.uuid4().hex[:8]}"
        user_uid = f"usr_{uuid.uuid4().hex[:8]}"
        admin = User(id=admin_uid, email=f"{admin_uid}@example.com", password_hash="pw", role="admin")
        user = User(id=user_uid, email=f"{user_uid}@example.com", password_hash="pw", role="member")
        db.add_all([admin, user])
        await db.commit()

        # Create 2 tickets and replies
        t1 = await create_ticket(db, user, "billing", "Billing Issue 1", "Need help with invoice")
        await create_ticket(db, user, "technical", "Technical Issue 2", "API 500 error")

        await add_reply(db, t1.id, admin, "We are reviewing your invoice")
        await add_reply(db, t1.id, user, "Thank you for the fast response")

        # 1. list_user_tickets batches reply counts
        tickets = await list_user_tickets(db, user_uid, limit=10, offset=0)
        assert len(tickets) >= 2
        t1_item = next(t for t in tickets if t["id"] == t1.id)
        assert t1_item["replies_count"] == 2

        # 2. get_ticket_details batches sender emails
        details = await get_ticket_details(db, t1.id, user)
        assert len(details["replies"]) == 2
        assert details["replies"][0]["user_email"] == admin.email
        assert details["replies"][1]["user_email"] == user.email

        # 3. list_admin_tickets batches user emails and supports limit/offset
        admin_tickets = await list_admin_tickets(db, status_filter="all", limit=5, offset=0)
        assert len(admin_tickets) >= 2
        assert all("user_email" in t for t in admin_tickets)


@pytest.mark.asyncio
async def test_discovery_provider_outage_and_refund():
    """F29 & F54: Provider outages mark discover jobs failed with provider_outage and refund credits."""
    from app.services.discover_service import _run_discovery_pipeline, DISCOVER_SEARCH_CREDIT_COST
    from app.services.scraping.ad_library_provider import AdLibraryProvider

    async with worker_session_maker() as db:
        test_uid = f"usr_disc_{uuid.uuid4().hex[:8]}"
        test_oid = f"org_disc_{uuid.uuid4().hex[:8]}"
        u = User(id=test_uid, email=f"{test_uid}@example.com", password_hash="pw", role="member")
        o = Organization(id=test_oid, name="Disc Org", owner_id=test_uid, plan="pro", credit_balance=100.0)
        db.add(u)
        await db.flush()
        db.add(o)
        await db.commit()
        await _grant_workspace(db, o, u, _PHASE6_FLAGS)

        job_id = f"job_outage_{uuid.uuid4().hex[:8]}"
        job = ScrapeJob(id=job_id, org_id=test_oid, query="test brand", status="running")
        db.add(job)
        await db.commit()

        # Simulate provider outage in AdLibraryProvider: all providers fail or are unconfigured
        async def fake_search(self_instance, query, **kwargs):
            self_instance.provider_outage = True
            self_instance.sources_tried = ["Metapi (unconfigured)", "Adyntel (unconfigured)", "Meta (unconfigured)", "Apify (unconfigured)"]
            return []

        # Use a real debit/refund transaction and enforce the actual function
        # signature. AsyncMock(spec=...) alone accepts invalid call arguments.
        from app.services.billing_service import charge, refund as refund_fn
        from app.models.usage_log import UsageLog
        await charge(db, o, test_uid, DISCOVER_SEARCH_CREDIT_COST, "test", "discover_search",
                     job_id=job_id, idempotency_key=f"phase6-{job_id}")
        autospec_refund = create_autospec(refund_fn, side_effect=refund_fn)
        with patch.object(AdLibraryProvider, "search", fake_search), \
             patch("app.services.discover_service.async_session_maker", worker_session_maker), \
             patch("app.services.discover_service.check_global_cap_and_log_preflight") as mock_cap, \
             patch("app.services.discover_service.refund", autospec_refund), \
             patch("app.services.discover_service.analyze_entity_intent", new_callable=AsyncMock, return_value={"entity_type": "general"}), \
             patch("app.services.work_outbox.retries_remaining", new_callable=AsyncMock, return_value=False):
            mock_cap.return_value = MagicMock(id="usage_123")
            await _run_discovery_pipeline(job_id, "test brand", {})

            await db.refresh(job)
            assert job.status == "failed"
            assert job.failure_kind == "provider_outage"
            assert "Provider Outage" in (job.stage_label or "")

            autospec_refund.assert_awaited_once()
            args, kwargs = autospec_refund.await_args
            assert kwargs == {}
            assert args[1:] == (test_oid, DISCOVER_SEARCH_CREDIT_COST, "provider_outage", job_id)
            await db.refresh(o)
            assert o.credit_balance == 100.0
            refunds = (await db.execute(select(UsageLog).where(
                UsageLog.job_id == job_id, UsageLog.credits_deducted < 0,
            ))).scalars().all()
            assert len(refunds) == 1
            assert refunds[0].operation == "refund_provider_outage"
            assert refunds[0].credits_deducted == -DISCOVER_SEARCH_CREDIT_COST






@pytest.mark.asyncio
async def test_insight_extended_fields_persistence_and_no_row_lock():
    """F41 & F65: Insight generation does not lock org row during LLM call and persists/unpacks extended fields."""
    from app.services.analysis_service import generate_insight_for_creative, get_creative_insight
    from app.schemas.analysis import Insight

    async with worker_session_maker() as db:
        test_uid = f"usr_ai_{uuid.uuid4().hex[:8]}"
        test_oid = f"org_ai_{uuid.uuid4().hex[:8]}"
        u = User(id=test_uid, email=f"{test_uid}@example.com", password_hash="pw", role="member")
        o = Organization(id=test_oid, name="AI Org", owner_id=test_uid, plan="pro", credit_balance=100.0)
        db.add(u)
        await db.flush()
        db.add(o)
        await db.commit()
        await _grant_workspace(db, o, u, _PHASE6_FLAGS)

        job = ScrapeJob(id=f"job_ai_{uuid.uuid4().hex[:8]}", org_id=test_oid, query="shoes", status="succeeded")
        db.add(job)
        await db.commit()

        creative = Creative(
            id=f"crt_{uuid.uuid4().hex[:8]}",
            job_id=job.id,
            brand_id="brand_1",
            platform="meta",
            headline="Revolutionary running shoe",
            body="Run faster with zero knee pain. Money back guarantee.",
            format="video"
        )
        db.add(creative)
        await db.commit()

        # Mock LLM provider
        mock_insight = Insight(
            id=f"ins_{uuid.uuid4().hex[:8]}",
            creative_id=creative.id,
            kind="opportunity",
            title="Biomechanical Breakthrough Hook",
            summary="Hooks runner segment by promising zero joint pain.",
            confidence=0.92,
            evidence_creative_ids=[creative.id],
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            model_version="v2.0",
            emotional_resonance="Relieves athletic frustration and fear of injury.",
            script_teardown="• 0-3s: Joint impact slow motion\n• 3-10s: Proprietary cushion test",
            fatigue_prediction="High durability evergreen angle.",
            key_elements=["joint protection", "slow motion hook", "money back guarantee"],
            recommendations=["Test 3 alternative visual hooks"]
        )

        mock_provider = MagicMock()
        mock_provider.generate_insight = AsyncMock(return_value=mock_insight)
        mock_provider.model = "groq/gpt-oss-120b"

        with patch("app.services.ai.ai_router.AIRouter.get_provider_for_user", new_callable=AsyncMock, return_value=mock_provider), \
             patch("app.services.analysis_service.assert_can_spend", wraps=__import__("app.services.billing_service", fromlist=["assert_can_spend"]).assert_can_spend) as mock_spend:

            gen_result = await generate_insight_for_creative(
                db=db,
                creative_id=creative.id,
                user=u,
                user_org_ids=[test_oid]
            )

            # F65 verification: assert_can_spend was called with lock_row=False
            assert mock_spend.call_args[1]["lock_row"] is False

            assert gen_result.emotional_resonance == "Relieves athletic frustration and fear of injury."
            assert gen_result.fatigue_prediction == "High durability evergreen angle."

            # F41 verification: Fetch insight via get_creative_insight and verify extended fields were unpacked from DB
            paginated = await get_creative_insight(db, creative.id, user_org_ids=[test_oid])
            assert len(paginated.items) >= 1
            fetched = paginated.items[0]
            assert fetched.emotional_resonance == "Relieves athletic frustration and fear of injury."
            assert fetched.script_teardown == "• 0-3s: Joint impact slow motion\n• 3-10s: Proprietary cushion test"
            assert fetched.fatigue_prediction == "High durability evergreen angle."
            assert fetched.key_elements == ["joint protection", "slow motion hook", "money back guarantee"]
            assert fetched.recommendations == ["Test 3 alternative visual hooks"]
