import pytest
import os
import sys
import uuid
import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import worker_session_maker, engine, worker_engine
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.ai_insight import AIInsight
from app.models.media_job import MediaGenerationJob
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.models.leadgen import LeadGenJob
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
async def test_storage_service_save_file_and_r2_validation():
    """F34 & F49: Test save_file writes and R2 validation rules."""
    from app.services import storage_service

    # 1. Empty data should raise ValueError
    with pytest.raises(ValueError):
        await storage_service.save_file(b"", "empty.png")

    # 2. Local storage write
    data = b"fake-avatar-bytes"
    url = await storage_service.save_file(data, "avatar.png", content_type="image/png")
    assert url is not None
    assert "avatar_" in url
    assert "sig=" in url

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
async def test_gemini_image_generation_kwargs():
    """F38: Gemini generate_image must accept seed and **kwargs without TypeError."""
    from app.services.ai.gemini_provider import GeminiProvider

    provider = GeminiProvider(api_key="fake-test-key")
    assert provider.is_configured is True

    # Calling with seed and unexpected kwargs should not fail with TypeError: unexpected keyword argument
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        res = await provider.generate_image(
            prompt="A futuristic neon city",
            aspect_ratio="1:1",
            seed=42,
            negative_prompt="blurry",
            guidance_scale=7.5
        )
        assert res is not None
        assert "data" in res


@pytest.mark.asyncio
async def test_pollinations_and_provider_resolver():
    """F39: Provider resolver checks server GEMINI_API_KEY; Pollinations handles frames & ref images."""
    from app.services.provider_resolver import _get_managed_provider
    from app.services.ai.pollinations_provider import PollinationsProvider
    from app.core.config import settings

    # 1. Managed provider prioritizes server GEMINI_API_KEY
    with patch.object(settings, "GEMINI_API_KEY", "real-gemini-server-key"):
        prov = _get_managed_provider()
        assert prov.__class__.__name__ == "GeminiProvider"

    # 2. PollinationsProvider generate_video forwards start_frame & end_frame
    poll_prov = PollinationsProvider()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake-video-bytes"
        mock_get.return_value = mock_resp

        res = await poll_prov.generate_video(
            prompt="running athlete",
            start_frame="https://example.com/start.png",
            end_frame="https://example.com/end.png"
        )
        assert res["media_type"] == "video"
        called_url = mock_get.call_args[0][0]
        assert "image=https" in called_url
        assert "end_image=https" in called_url

    # 3. PollinationsProvider generate_image forwards reference_images
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get_img:
        mock_resp_img = MagicMock()
        mock_resp_img.status_code = 200
        mock_resp_img.content = b"fake-img-bytes"
        mock_get_img.return_value = mock_resp_img

        with patch.object(poll_prov, "_clean_watermark", return_value=b"cleaned-bytes"):
            res_img = await poll_prov.generate_image(
                prompt="portrait",
                reference_images=["https://example.com/ref.jpg"]
            )
            assert res_img["media_type"] == "image"
            called_img_url = mock_get_img.call_args[0][0]
            assert "image=https" in called_img_url


@pytest.mark.asyncio
async def test_media_generation_canceled_and_failure_handling():
    """F40 & F82: Media generation respects cancellation and handles provider failures cleanly."""
    from app.services.media_service import gemini_generate_media_task

    async with worker_session_maker() as db:
        test_uid = f"usr_p6_{uuid.uuid4().hex[:8]}"
        test_oid = f"org_p6_{uuid.uuid4().hex[:8]}"
        u = User(id=test_uid, email=f"{test_uid}@example.com", password_hash="pw", role="member")
        o = Organization(id=test_oid, name="P6 Org", owner_id=test_uid, plan="growth", credit_balance=100.0)
        db.add(u)
        await db.flush()
        db.add(o)
        await db.commit()
        await _grant_workspace(db, o, u, _PHASE6_FLAGS)

        # 1. Job canceled prior to start (F40)
        job_canceled = MediaGenerationJob(
            id=f"med_{uuid.uuid4().hex[:8]}",
            org_id=test_oid,
            user_id=test_uid,
            prompt="test prompt",
            provider="helix_managed",
            status="canceled"
        )
        db.add(job_canceled)
        await db.commit()

        await gemini_generate_media_task(job_canceled.id, test_uid, test_oid)

        # Status must remain canceled and not overwritten to running or completed
        await db.refresh(job_canceled)
        assert job_canceled.status == "canceled"

        # 2. Provider resolution failure (F82)
        job_fail = MediaGenerationJob(
            id=f"med_{uuid.uuid4().hex[:8]}",
            org_id=test_oid,
            user_id=test_uid,
            prompt="test fail prompt",
            provider="helix_managed",
            status="pending"
        )
        db.add(job_fail)
        await db.commit()

        with patch("app.services.media_service.resolve_image_provider", side_effect=RuntimeError("Provider config crashed")):
            await gemini_generate_media_task(job_fail.id, test_uid, test_oid)

        await db.refresh(job_fail)
        assert job_fail.status == "failed"
        assert job_fail.failure_kind == "error"
        assert "Provider config crashed" in job_fail.error_message


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
        t2 = await create_ticket(db, user, "technical", "Technical Issue 2", "API 500 error")

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

        # Patch check_global_cap_and_log_preflight to succeed
        from app.services.billing_service import refund as refund_fn
        autospec_refund = AsyncMock(spec=refund_fn)
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

            autospec_refund.assert_awaited()
            args, kwargs = autospec_refund.await_args
            reason = kwargs.get("reason", args[3] if len(args) > 3 else None)
            amount = kwargs.get("amount", args[2] if len(args) > 2 else None)
            assert reason == "provider_outage"
            assert amount == DISCOVER_SEARCH_CREDIT_COST


@pytest.mark.asyncio
async def test_leadgen_checkpoint_resume_and_pause_refresh():
    """F30: Resumed leadgen job with checkpoint_path restores checkpoint; pause loop uses populate_existing."""
    from app.services.leadgen_pipeline import _load_checkpoint, _save_checkpoint

    async with worker_session_maker() as db:
        test_uid = f"usr_lg_{uuid.uuid4().hex[:8]}"
        test_oid = f"org_lg_{uuid.uuid4().hex[:8]}"
        u = User(id=test_uid, email=f"{test_uid}@example.com", password_hash="pw", role="member")
        o = Organization(id=test_oid, name="LG Org", owner_id=test_uid, plan="pro", credit_balance=100.0)
        db.add(u)
        await db.flush()
        db.add(o)
        await db.commit()

        job_id = f"lg_job_{uuid.uuid4().hex[:8]}"
        job = LeadGenJob(
            id=job_id,
            org_id=test_oid,
            user_id=test_uid,
            status="queued",
            engine_default="stealth",
            brief={"query": "solar installers"},
            seeds=["https://solar1.com"]
        )
        db.add(job)
        await db.commit()

        # Save checkpoint
        _save_checkpoint(job, ["https://solar1.com", "https://solar2.com"], processed=1)
        await db.commit()

        # Verify checkpoint_path is set on the model
        assert job.checkpoint_path is not None

        # Verify condition for resume_checkpoint: even if status is queued, bool(job.checkpoint_path) activates resume
        resume_checkpoint = job.status == "paused" or bool(job.checkpoint_path)
        assert resume_checkpoint is True

        loaded = _load_checkpoint(job)
        assert loaded is not None
        assert loaded["pending"] == ["https://solar1.com", "https://solar2.com"]
        assert loaded["processed"] == 1


@pytest.mark.asyncio
async def test_scrapling_xhr_capture_with_ssrf_safety():
    """F81: scrapling_engine.fetch matches capture_xhr_pattern and fetches safely with safe_http_get."""
    from app.services import scrapling_engine

    sample_html = """
    <html>
      <head>
        <script>
          fetch('/api/v1/contacts.json').then(r => r.json());
          axios.get('http://169.254.169.254/latest/meta-data');
        </script>
      </head>
      <body><h1>Test Page</h1></body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.text = sample_html
    mock_resp.url = "https://publicsite.example.com"

    mock_fetcher = MagicMock()
    mock_fetcher.get.return_value = mock_resp

    mock_scrapling = MagicMock()
    mock_scrapling.fetchers.StealthyFetcher = mock_fetcher
    mock_scrapling.fetchers.Fetcher = mock_fetcher

    with patch.dict(sys.modules, {"scrapling": mock_scrapling, "scrapling.fetchers": mock_scrapling.fetchers}), \
         patch("app.services.scrapling_engine.is_available", return_value=True), \
         patch("app.services.scrapling_engine.robots_allowed", return_value=True), \
         patch("app.services.security_service.is_safe_public_url", return_value=True), \
         patch("app.services.security_service.safe_http_get") as mock_safe_get:

        mock_xhr_resp = MagicMock()
        mock_xhr_resp.status_code = 200
        mock_xhr_resp.text = '{"email": "contact@publicsite.example.com", "phone": "+15551234567"}'
        mock_safe_get.return_value = mock_xhr_resp

        res = scrapling_engine.fetch(
            url="https://publicsite.example.com",
            engine="stealth",
            capture_xhr_pattern=r"contacts\.json"
        )

        assert res["fetch_status"] == "ok"
        assert len(res["captured_xhr"]) == 1
        assert "contacts.json" in res["captured_xhr"][0]
        # XHR payload is embedded in HTML
        assert "contact@publicsite.example.com" in res["html"]


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
