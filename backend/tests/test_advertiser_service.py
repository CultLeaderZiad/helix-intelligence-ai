"""3.2 Advertiser page and winner signals, on a real database."""
import datetime
import uuid

import pytest
from fastapi import HTTPException

from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.monitor import Monitor, MonitorCreative
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import advertiser_service


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


async def _workspace(db, s):
    user = User(id=f"u_adv_{s}", email=f"adv-{s}@example.com", password_hash="x", role="member")
    db.add(user)
    await db.flush()
    org = Organization(id=f"o_adv_{s}", name="ADV", owner_id=user.id, plan="pro")
    db.add(org)
    await db.flush()
    return user, org


def _ad(job_id, brand, headline, body, domain, **kw):
    return Creative(job_id=job_id, brand_id=brand, brand_name="Acme", platform="meta", format="image",
                    headline=headline, body=body, cta="Shop now", landing_domain=domain, **kw)


@pytest.mark.asyncio
async def test_winner_signals_are_real_components_and_unknown_stays_unknown():
    s = uuid.uuid4().hex[:8]
    brand = f"acme_{s}"
    async with async_session_maker() as db:
        _u, org = await _workspace(db, s)
        job1 = ScrapeJob(org_id=org.id, query="acme", status="succeeded")
        job2 = ScrapeJob(org_id=org.id, query="acme 2", status="succeeded")
        db.add_all([job1, job2])
        await db.flush()
        db.add_all([
            _ad(job1.id, brand, "Summer sale", "50% off", "acme.com", days_active=40, source_ad_id=f"a1{s}"),
            _ad(job1.id, brand, "Summer sale", "Now 60% off", "acme.com", days_active=12, source_ad_id=f"a2{s}"),
            _ad(job1.id, brand, "Gift guide", "Gifts", "acme.com", source_ad_id=f"b{s}"),  # no dates at all
            _ad(job1.id, brand, "Other site", "x", "promo.acme.io", first_seen="2026-11-01", last_seen="2026-11-10",
                source_ad_id=f"c{s}"),
            # The same ad found again by another search: one ad, not two.
            _ad(job2.id, brand, "Summer sale", "50% off", "acme.com", days_active=40, source_ad_id=f"a1{s}"),
        ])
        await db.commit()

    async with async_session_maker() as db:
        out = await advertiser_service.winners(db, [org.id], brand, 1, 20)
    assert out["total"] == 4
    heads = [(i["headline"], i["signals"]["days_active"]) for i in out["items"]]
    assert heads[0] == ("Summer sale", 40)
    assert heads[-1] == ("Gift guide", None)  # unknown is listed last, never as 0
    first = out["items"][0]["signals"]
    assert first["variants"] == 2  # same identity, different copy
    assert first["landing_page_reuse"] == 3
    other = next(i for i in out["items"] if i["headline"] == "Other site")
    assert other["signals"]["days_active"] == 10 and other["signals"]["landing_page_reuse"] == 1


@pytest.mark.asyncio
async def test_another_workspace_sees_nothing():
    s = uuid.uuid4().hex[:8]
    brand = f"acme_{s}"
    async with async_session_maker() as db:
        _u, org = await _workspace(db, s)
        _u2, other = await _workspace(db, s + "x")
        job = ScrapeJob(org_id=org.id, query="acme", status="succeeded")
        db.add(job)
        await db.flush()
        db.add(_ad(job.id, brand, "H", "B", "acme.com", days_active=3))
        await db.commit()
    async with async_session_maker() as db:
        assert (await advertiser_service.winners(db, [other.id], brand, 1, 20))["total"] == 0
        with pytest.raises(HTTPException) as exc:
            await advertiser_service.summary(db, [other.id], brand)
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_summary_counts_launches_from_monitors_and_not_the_baseline():
    s = uuid.uuid4().hex[:8]
    brand = f"acme_{s}"
    baseline = _now() - datetime.timedelta(days=20)
    async with async_session_maker() as db:
        user, org = await _workspace(db, s)
        job = ScrapeJob(org_id=org.id, query="acme", status="succeeded")
        db.add(job)
        await db.flush()
        old = _ad(job.id, brand, "Old", "x", "acme.com", days_active=90)
        new = _ad(job.id, brand, "New", "y", "acme.com")
        db.add_all([old, new])
        monitor = Monitor(org_id=org.id, user_id=user.id, name="Acme", query="acme", baseline_at=baseline)
        db.add(monitor)
        await db.flush()
        db.add_all([
            MonitorCreative(monitor_id=monitor.id, identity_hash=f"i1{s}", content_hash="c1", creative_id=old.id,
                            status="active", first_seen_at=baseline, last_seen_at=_now()),
            MonitorCreative(monitor_id=monitor.id, identity_hash=f"i2{s}", content_hash="c2", creative_id=new.id,
                            status="active", first_seen_at=_now() - datetime.timedelta(days=3), last_seen_at=_now()),
        ])
        await db.commit()
    async with async_session_maker() as db:
        out = await advertiser_service.summary(db, [org.id], brand)
    assert out["brand_name"] == "Acme" and out["ads_found"] == 2
    assert out["launches_last_30d"] == 1  # the baseline ad is not a launch
    assert out["active_now"] == 2
    assert out["longest_running_days"] == 90 and out["ads_with_known_run_length"] == 1
    assert len(out["weekly"]) == advertiser_service.WEEKS and sum(w["launches"] for w in out["weekly"]) == 1


@pytest.mark.asyncio
async def test_without_monitors_time_series_is_absent_not_zero():
    s = uuid.uuid4().hex[:8]
    brand = f"acme_{s}"
    async with async_session_maker() as db:
        _u, org = await _workspace(db, s)
        job = ScrapeJob(org_id=org.id, query="acme", status="succeeded")
        db.add(job)
        await db.flush()
        db.add(_ad(job.id, brand, "H", "B", "acme.com"))
        await db.commit()
    async with async_session_maker() as db:
        out = await advertiser_service.summary(db, [org.id], brand)
    assert out["weekly"] == [] and out["launches_last_30d"] is None and out["active_now"] is None
    assert out["longest_running_days"] is None
