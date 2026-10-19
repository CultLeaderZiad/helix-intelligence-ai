"""W2 provider, ledger, and worker boundaries.

Uses the disposable migrated database when a test touches Postgres.
Provider calls use a mock transport or an injected outcome. No live vendor.
"""

from __future__ import annotations

import asyncio
import socket
import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from unittest.mock import AsyncMock, patch

from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.scout import ScoutMapsJob, ScoutMapsLead
from app.models.user import User
from app.models.work_item import WorkItem
from app.services.ai.base import AIProvider
from app.services.ai.structured import InvalidModelOutput, parse_insight, parse_translation
from app.services.billing_service import (
    DISCOVER_SEARCH_CREDIT_COST,
    charge,
    release_reservation,
    reserve_credits,
)
from app.services.maps_scout_service import _optional_float, _optional_int
from app.services.safe_fetch import UnsafeFetch, safe_http_get
from app.services.work_outbox import claim_next_work_item, enqueue_work, requeue_expired_leases
from app.schemas.creative import Creative as CreativeSchema


def _public_resolve(hostname, port):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def test_streaming_byte_cap_uses_mock_transport_not_a_replaced_helper():
    def handler(request):
        assert request.url.host == "example.com"
        return httpx.Response(200, content=b"x" * 40)

    with pytest.raises(UnsafeFetch):
        safe_http_get(
            "https://example.com/file",
            max_bytes=8,
            transport=httpx.MockTransport(handler),
            resolve=_public_resolve,
        )


def test_mock_transport_redirect_is_rechecked():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})

    with pytest.raises(UnsafeFetch):
        safe_http_get(
            "https://example.com/start",
            max_bytes=100,
            transport=httpx.MockTransport(handler),
            resolve=_public_resolve,
        )


def test_incomplete_insight_and_canned_translation_are_rejected():
    with pytest.raises(InvalidModelOutput):
        parse_insight({}, creative_id="creative-1", model_version="groq/test:insight-v2")
    with pytest.raises(InvalidModelOutput):
        parse_translation(
            {
                "detected_lang": "es",
                "translated_text": "Naturia Parasite Cleansing Drops eliminate the biofilm",
                "breakdown": {"hook": "a", "problem": "b", "solution": "c", "cta": "d"},
            },
            target_lang="en",
        )


@pytest.mark.asyncio
async def test_provider_http_exception_is_not_unbound_local():
    class Boom(AIProvider):
        async def _call_api(self, messages):
            raise HTTPException(status_code=503, detail="provider down")

    creative = CreativeSchema(
        id="creative-1",
        brand_id="brand",
        platform="meta",
        format="image",
        headline="Hello",
        body="Body",
        cta="Shop",
        variant_count=1,
        scores={"hook": None, "clarity": None, "retention": None, "composite": None},
        metrics={},
        pattern_ids=[],
    )
    with pytest.raises(HTTPException) as exc:
        await Boom().generate_insight(creative)
    assert exc.value.status_code == 503
    assert "provider down" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_meta_http_failure_is_not_counted_as_success():
    from app.services.scraping.ad_library_provider import AdLibraryProvider

    provider = AdLibraryProvider()
    provider.meta_token = "meta-test"
    provider.metapi_provider.metapi_api_key = None
    provider.adyntel_provider.adyntel_api_key = None
    provider.apify_token = None

    class Response:
        status_code = 500
        text = "unavailable"

        def json(self):
            return {}

    with patch("app.services.safe_fetch.safe_request_async", new=AsyncMock(return_value=Response())):
        rows = await provider.search("nike.com", max_records=5)
    assert rows == []
    assert provider.provider_outage is True
    assert provider.successful_queries_count == 0


@pytest.mark.asyncio
async def test_missing_rating_persists_as_null():
    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=10)
        db.add(user)
        await db.flush()
        db.add(org)
        job = ScoutMapsJob(id=f"mj_{suffix}", org_id=org.id, user_id=user.id, keyword="clinics", city="Cairo")
        db.add(job)
        await db.flush()
        lead = ScoutMapsLead(
            id=f"ml_{suffix}",
            job_id=job.id,
            org_id=org.id,
            title="Clinic with no rating",
            metadata_raw={
                "rating": {"value": None, "provider": "overpass", "source_url": "https://overpass-api.de/api/interpreter", "fetched_at": "2026-10-18T00:00:00+00:00"},
                "reviews_count": {"value": None, "provider": "overpass", "source_url": "https://overpass-api.de/api/interpreter", "fetched_at": "2026-10-18T00:00:00+00:00"},
            },
        )
        lead.rating = _optional_float(None)
        lead.reviews_count = _optional_int(None)
        db.add(lead)
        await db.commit()
        stored = await db.get(ScoutMapsLead, lead.id)
        assert stored.rating is None
        assert stored.reviews_count is None
        assert stored.metadata_raw["rating"]["value"] is None
        assert stored.metadata_raw["reviews_count"]["source_url"]


@pytest.mark.asyncio
async def test_reservation_is_single_debit_and_release_is_idempotent():
    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=5)
        db.add(user)
        await db.flush()
        db.add(org)
        await db.commit()
        org_id = org.id
        user_id = user.id

    async def hold(key):
        async with worker_session_maker() as db:
            org = await db.get(Organization, org_id)
            return await reserve_credits(
                db, org, user_id, 1, "ai_insight", idempotency_key=key, metadata={"creative_id": "c1"}
            )

    first, second = await asyncio.gather(hold("same-key"), hold("same-key"))
    assert first.id == second.id
    async with worker_session_maker() as db:
        org = await db.get(Organization, org_id)
        assert float(org.credit_balance) == 4
        released = await release_reservation(db, first.id, "test_release")
        assert released is True
        again = await release_reservation(db, first.id, "test_release")
        assert again is False
        org = await db.get(Organization, org_id)
        assert float(org.credit_balance) == 5
        kinds = (await db.execute(text(
            "SELECT entry_kind FROM credit_ledger WHERE org_id = :org ORDER BY created_at"
        ), {"org": org_id})).scalars().all()
        assert kinds == ["debit", "refund"]


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_overdraw():
    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=1)
        db.add(user)
        await db.flush()
        db.add(org)
        await db.commit()
        org_id = org.id
        user_id = user.id

    async def hold(key):
        async with worker_session_maker() as db:
            org = await db.get(Organization, org_id)
            return await reserve_credits(
                db, org, user_id, 1, "ai_insight", idempotency_key=key, metadata={"creative_id": key}
            )

    results = await asyncio.gather(hold("one"), hold("two"), return_exceptions=True)
    failures = [item for item in results if isinstance(item, HTTPException)]
    holds = [item for item in results if not isinstance(item, Exception)]
    assert len(holds) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 402
    async with worker_session_maker() as db:
        org = await db.get(Organization, org_id)
        assert float(org.credit_balance) == 0


@pytest.mark.asyncio
async def test_expired_lease_is_requeued_then_dead_lettered():
    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        await db.execute(text("UPDATE work_items SET status = 'dead' WHERE status IN ('queued', 'leased')"))
        await db.commit()
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=3)
        db.add(user)
        await db.flush()
        db.add(org)
        await db.commit()
        item = await enqueue_work(db, kind="discover", job_id=f"job_{suffix}", org_id=org.id, user_id=user.id, payload={"query": "nike"})
        item_id = item.id

    claimed = await claim_next_work_item("worker-a")
    assert claimed == item_id
    async with worker_session_maker() as db:
        row = await db.get(WorkItem, item_id)
        row.lease_until = row.lease_until.replace(year=2000)
        await db.commit()
    assert await requeue_expired_leases() == 1
    async with worker_session_maker() as db:
        row = await db.get(WorkItem, item_id)
        assert row.status == "queued"
        attempts = row.attempt_count
        row.available_at = row.created_at
        await db.commit()
    assert await claim_next_work_item("worker-b") == item_id
    async with worker_session_maker() as db:
        row = await db.get(WorkItem, item_id)
        row.max_attempts = row.attempt_count
        row.lease_until = row.lease_until.replace(year=2000)
        await db.commit()
        assert attempts == 1
    assert await requeue_expired_leases() == 1
    async with worker_session_maker() as db:
        row = await db.get(WorkItem, item_id)
        assert row.status == "dead"


@pytest.mark.asyncio
async def test_provider_outage_keeps_state_and_refunds_the_ledger():
    from app.services.discover_service import _run_discovery_pipeline
    from app.services.scraping.ad_library_provider import AdLibraryProvider

    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=10)
        db.add(user)
        await db.flush()
        db.add(org)
        await db.commit()
        from app.models.access_grant import OrganizationAccessGrant
        db.add(OrganizationAccessGrant(
            org_id=org.id,
            plan_id="plan_pro",
            feature_flags={"discover": True, "intelligence": True, "create": True},
            granted_by_user_id=user.id,
        ))
        await db.commit()
        await charge(db, org, user.id, DISCOVER_SEARCH_CREDIT_COST, "discover_composite", "discover_job_start", job_id=f"job_{suffix}")
        job = ScrapeJob(id=f"job_{suffix}", org_id=org.id, query="nike", status="running")
        db.add(job)
        await db.commit()
        org_id = org.id
        job_id = job.id

    async def fake_search(self_instance, query, **kwargs):
        self_instance.provider_outage = True
        self_instance.sources_tried = ["Meta Graph API"]
        return []

    with patch.object(AdLibraryProvider, "search", fake_search), \
         patch("app.services.discover_service.async_session_maker", worker_session_maker), \
         patch("app.services.discover_service.check_global_cap_and_log_preflight", new=AsyncMock(return_value=type("U", (), {"id": "usage"})())), \
         patch("app.services.discover_service.analyze_entity_intent", new=AsyncMock(return_value={"entity_type": "general"})), \
         patch("app.services.work_outbox.retries_remaining", new=AsyncMock(return_value=False)):
        await _run_discovery_pipeline(job_id, "nike", {})

    async with worker_session_maker() as db:
        job = await db.get(ScrapeJob, job_id)
        org = await db.get(Organization, org_id)
        assert job.status == "failed"
        assert job.failure_kind == "provider_outage"
        assert float(org.credit_balance) == 10
        refunds = (await db.execute(text(
            "SELECT count(*) FROM credit_ledger WHERE org_id = :org AND entry_kind = 'refund'"
        ), {"org": org_id})).scalar_one()
        assert refunds == 1
