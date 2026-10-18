"""Focused checks for the W2 leftovers that still collapsed unknowns into zeros."""

from __future__ import annotations

import uuid

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.api.routers.scout import csv_metric
from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.pattern import Pattern
from app.models.scout import ScoutMapsJob, ScoutMapsLead
from app.models.user import User
from app.services.scraping.base import ProviderFailure, RawCreative
from app.services.scraping.normalizer import normalize_creative


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(self.status_code),
            )


@pytest.mark.asyncio
async def test_adyntel_http_and_transport_errors_are_typed_failures():
    from app.services.scraping.adyntel_provider import AdyntelProvider

    provider = AdyntelProvider(None, "org", "user")
    provider.adyntel_api_key = "adyntel-key"
    provider.adyntel_email = "owner@example.com"

    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(return_value=_Response(503, {"error": "down"})),
    ):
        with pytest.raises(ProviderFailure) as raised:
            await provider.search("example.com", max_records=5)
    assert raised.value.provider == "adyntel"
    assert raised.value.http_status == 503
    assert provider.last_outcome == "failure"

    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    ):
        with pytest.raises(ProviderFailure) as raised:
            await provider.search("example.com", max_records=5)
    assert raised.value.provider == "adyntel"
    assert provider.last_outcome == "failure"


@pytest.mark.asyncio
async def test_adyntel_empty_200_stays_empty_and_library_does_not_count_a_failure():
    from app.services.scraping.ad_library_provider import AdLibraryProvider
    from app.services.scraping.adyntel_provider import AdyntelProvider

    provider = AdyntelProvider(None, "org", "user")
    provider.adyntel_api_key = "adyntel-key"
    provider.adyntel_email = "owner@example.com"
    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(return_value=_Response(200, {"results": []})),
    ):
        rows = await provider.search("example.com", max_records=5)
    assert rows == []
    assert provider.last_outcome == "empty"

    library = AdLibraryProvider()
    library.meta_token = None
    library.metapi_provider.metapi_api_key = None
    library.apify_token = None
    library.adyntel_provider.adyntel_api_key = "adyntel-key"
    library.adyntel_provider.adyntel_email = "owner@example.com"
    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(side_effect=httpx.ConnectError("down")),
    ):
        rows = await library.search("example.com", max_records=5)
    assert rows == []
    assert library.successful_queries_count == 0
    assert library.provider_outage is True


@pytest.mark.asyncio
async def test_scrapegraph_landing_extract_failures_are_typed():
    from app.services.scraping.scrapegraph_provider import ScrapeGraphProvider

    missing = ScrapeGraphProvider()
    missing.api_key = None
    skipped = await missing.extract_landing_page("https://example.com")
    assert skipped["status"] == "skipped"
    assert skipped != {}

    provider = ScrapeGraphProvider()
    provider.api_key = "sg-test"
    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(return_value=_Response(500, {"error": "down"})),
    ):
        failed = await provider.extract_landing_page("https://example.com/landing")
    assert failed["status"] == "failure"
    assert failed["provider"] == "scrapegraph"
    assert failed["headline"] is None
    assert failed != {}

    with patch(
        "app.services.safe_fetch.safe_request_async",
        new=AsyncMock(return_value=_Response(200, {"json": {}})),
    ):
        empty = await provider.extract_landing_page("https://example.com/landing")
    assert empty["status"] == "empty"
    assert empty != {}


def test_normalizer_persists_provenance_fields():
    raw = RawCreative(
        platform="meta",
        brand_name="Acme",
        headline="Why this offer is different",
        body="A real body that is long enough to survive macro cleaning and stay a creative.",
        source_ad_id="ad-archive-9",
        permalink="https://www.facebook.com/ads/library/?id=ad-archive-9",
        fetched_at="2026-10-18T12:00:00+00:00",
        provider="adyntel",
        raw={"ad_archive_id": "ad-archive-9", "page_id": "page-1"},
        days_known=False,
    )
    created = normalize_creative(raw, job_id="job-1", brand_id="brand-1")
    assert created is not None
    creative, _score = created
    assert creative.source_ad_id == "ad-archive-9"
    assert creative.permalink == "https://www.facebook.com/ads/library/?id=ad-archive-9"
    assert creative.fetched_at is not None
    assert creative.fetched_at.isoformat().startswith("2026-10-18T12:00:00")
    assert creative.days_active is None
    assert creative.provenance_json["provider"] == "adyntel"
    assert creative.provenance_json["raw"]["ad_archive_id"] == "ad-archive-9"
    assert creative.ctr_est is None
    assert creative.engagement_rate is None


def test_csv_metric_keeps_zero_and_blanks_unknown():
    assert csv_metric(None) == ""
    assert csv_metric(0) == 0
    assert csv_metric(0.0) == 0.0
    assert csv_metric(4.5) == 4.5


@pytest.mark.asyncio
async def test_unmeasured_lift_and_reviews_persist_as_null_while_zero_stays_zero():
    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"{suffix}@example.com", password_hash="x", role="member")
        org = Organization(id=f"o_{suffix}", name="Org", owner_id=user.id, plan="pro", credit_balance=10)
        db.add(user)
        await db.flush()
        db.add(org)
        pattern = Pattern(
            id=f"pat_{suffix}",
            org_id=org.id,
            label="hook",
            family="copy",
            prevalence=0.2,
            lift_index=None,
        )
        job = ScoutMapsJob(id=f"mj_{suffix}", org_id=org.id, user_id=user.id, keyword="clinics", city="Cairo")
        db.add_all([pattern, job])
        await db.flush()
        unknown = ScoutMapsLead(
            id=f"ml_unknown_{suffix}",
            job_id=job.id,
            org_id=org.id,
            title="No rating",
            rating=None,
            reviews_count=None,
        )
        zero = ScoutMapsLead(
            id=f"ml_zero_{suffix}",
            job_id=job.id,
            org_id=org.id,
            title="Zero rating",
            rating=0,
            reviews_count=0,
        )
        db.add_all([unknown, zero])
        await db.commit()

        stored_pattern = await db.get(Pattern, pattern.id)
        stored_unknown = await db.get(ScoutMapsLead, unknown.id)
        stored_zero = await db.get(ScoutMapsLead, zero.id)
        assert stored_pattern.lift_index is None
        assert stored_unknown.rating is None
        assert stored_unknown.reviews_count is None
        assert stored_zero.rating == 0
        assert stored_zero.reviews_count == 0


@pytest.mark.asyncio
async def test_curated_dossier_does_not_ship_unfetched_profile_urls():
    from app.services.entity_intelligence import analyze_entity_intent

    profile = await analyze_entity_intent("sneako")
    assert profile["evidence_status"] == "curated_unverified"
    assert profile["social_links"]
    for entry in profile["social_links"].values():
        assert entry["fetched"] is False
        assert entry["profile_url"] is None
        assert entry["search_url"] is None
