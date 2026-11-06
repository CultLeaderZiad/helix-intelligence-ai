"""W8: Discover ordering is honored and only Meta-official rows carry reach/spend."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import creative_service
from app.services.scraping.base import RawCreative
from app.services.scraping.normalizer import normalize_creative


def _raw(**kwargs) -> RawCreative:
    return RawCreative(
        platform="meta",
        brand_name="Acme",
        headline="A headline that is long enough",
        body="A real body that is long enough to survive macro cleaning and stay a creative.",
        days_known=True,
        days_active=10,
        **kwargs,
    )


def test_a_source_that_does_not_say_meta_official_never_keeps_reach_or_spend():
    creative, _score = normalize_creative(_raw(impressions_est=50_000, spend_band="1k-5k"), job_id="j", brand_id="b")
    assert creative.data_source == "unknown"
    assert creative.impressions_est is None and creative.spend_band is None


def test_meta_official_keeps_its_reported_upper_bound():
    creative, _score = normalize_creative(
        _raw(impressions_est=50_000, data_source="meta_official", is_estimated=False), job_id="j", brand_id="b"
    )
    assert creative.impressions_est == 50_000


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs", [{"sort": "random"}, {"min_days": 14}, {"min_days": 45}, {"min_score": 11}, {"min_score": -1}])
async def test_unknown_sort_is_rejected_before_any_query(kwargs):
    class NoDB:
        async def scalar(self, *_):
            raise AssertionError("query ran")

        async def execute(self, *_):
            raise AssertionError("query ran")

    with pytest.raises(HTTPException) as error:
        await creative_service.list_creatives(NoDB(), job_id="j", **kwargs)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_results_follow_the_requested_sort_with_nulls_last():
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"w8-sort-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Sort", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        job = ScrapeJob(id=f"j_{suffix}", org_id=org.id, query="sort", status="succeeded")
        db.add(job)
        await db.flush()
        rows = [
            # id suffix, days_active, first_seen, impressions, composite
            ("a", 3, "2026-10-01", None, 9.0),
            ("b", 40, "2026-08-01", 2000, None),
            ("c", None, "2026-11-01", 500, 4.0),
        ]
        for key, days, first, impressions, composite in rows:
            db.add(Creative(id=f"c_{suffix}_{key}", job_id=job.id, brand_id="brand", brand_name="Brand",
                            platform="meta", format="image", days_active=days, first_seen=first,
                            impressions_est=impressions))
            db.add(CreativeScore(creative_id=f"c_{suffix}_{key}", composite=composite))
        await db.commit()

        async def order(sort):
            page = await creative_service.list_creatives(db, job_id=job.id, sort=sort, user_org_ids=[org.id])
            return [item.id.rsplit("_", 1)[1] for item in page.items]

        assert await order("days_active_desc") == ["b", "a", "c"]
        assert await order("first_seen_desc") == ["c", "a", "b"]
        assert await order("composite_desc") == ["a", "c", "b"]
        assert await order("impressions_desc") == ["b", "c", "a"]
        assert creative_service.DEFAULT_CREATIVE_SORT == "days_active_desc"

        # Longevity presets: unknown run length is excluded and counted, never 0.
        thirty = await creative_service.list_creatives(db, job_id=job.id, min_days=30, user_org_ids=[org.id])
        assert [item.id.rsplit("_", 1)[1] for item in thirty.items] == ["b"]
        assert thirty.total == 1 and thirty.hidden_unknown_run_length == 1
        assert (await creative_service.list_creatives(db, job_id=job.id, min_days=90, user_org_ids=[org.id])).total == 0
        unfiltered = await creative_service.list_creatives(db, job_id=job.id, user_org_ids=[org.id])
        assert unfiltered.hidden_unknown_run_length is None and unfiltered.total == 3
        rubric = await creative_service.list_creatives(db, job_id=job.id, min_score=5, user_org_ids=[org.id])
        assert [item.id.rsplit("_", 1)[1] for item in rubric.items] == ["a"]
