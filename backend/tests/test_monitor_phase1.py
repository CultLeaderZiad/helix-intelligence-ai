"""Phase 1 monitor reliability, on a real database.

- the reconciler closes a dead run and the monitor can run again;
- a run killed by a restart is retried early, at most MONITOR_RESTART_MAX_RETRIES times;
- a reached record budget leaves monitors unclaimed and uncharged;
- one full monitor lifecycle with a stubbed provider: baseline, a new ad,
  an ad missing once (kept), missing twice (killed).
"""
import datetime
import uuid

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.monitor import Monitor, MonitorCreative, MonitorRun
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import job_reconciliation, monitor_service


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


async def _seed(suffix, *, runs=(), next_run_at=None):
    async with async_session_maker() as db:
        user = User(id=f"u_p1_{suffix}", email=f"p1-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_p1_{suffix}", name="P1", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        monitor = Monitor(id=f"m_p1_{suffix}", org_id=org.id, user_id=user.id, name="M", query="q", cadence="daily",
                          next_run_at=next_run_at or (_now() + datetime.timedelta(hours=20)))
        db.add(monitor)
        await db.flush()
        for i, (status, reason, age_s) in enumerate(runs):
            db.add(MonitorRun(id=f"r{i}_{suffix}", monitor_id=monitor.id, status=status, skipped_reason=reason,
                              started_at=_now() - datetime.timedelta(seconds=age_s)))
        await db.commit()
    return monitor.id


async def _monitor(monitor_id):
    async with async_session_maker() as db:
        return (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one()


async def _run_rows(monitor_id):
    async with async_session_maker() as db:
        return (await db.execute(
            select(MonitorRun).where(MonitorRun.monitor_id == monitor_id).order_by(MonitorRun.started_at.desc())
        )).scalars().all()


@pytest.fixture
def quiet(monkeypatch):
    notes = []

    async def note(monitor_id, title, body):
        notes.append((monitor_id, title, body))

    monkeypatch.setattr(monitor_service, "_notify_owner", note)
    return notes


# --- 1. Sweep on a real DB -------------------------------------------------

@pytest.mark.asyncio
async def test_sweep_fails_a_dead_run_and_the_monitor_can_run_again(quiet, monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    old = settings.MONITOR_RUN_TIMEOUT_S + 600
    monitor_id = await _seed(suffix, runs=[("running", None, old)])

    swept = await job_reconciliation._sweep_monitor_runs()
    assert swept >= 1
    (run,) = await _run_rows(monitor_id)
    assert run.status == "failed" and run.skipped_reason == "service_restart"
    assert run.finished_at is not None
    assert any(m == monitor_id and "interrupted" in t.lower() for m, t, _ in quiet)

    # No 409: run_now accepts the monitor again.
    enqueued = []

    async def fake_enqueue(db, **kw):
        enqueued.append(kw["job_id"])

    monkeypatch.setattr("app.services.work_outbox.enqueue_work", fake_enqueue)
    monkeypatch.setattr("app.services.work_outbox.inline_execution_enabled", lambda: False)
    monitor = await _monitor(monitor_id)
    async with async_session_maker() as db:
        out = await monitor_service.run_now(db, monitor_id, monitor.org_id)
    assert out["success"] is True and enqueued == [monitor_id]


@pytest.mark.asyncio
async def test_a_live_run_is_left_alone(quiet):
    suffix = uuid.uuid4().hex[:8]
    monitor_id = await _seed(suffix, runs=[("running", None, 30)])
    await job_reconciliation._sweep_monitor_runs()
    (run,) = await _run_rows(monitor_id)
    assert run.status == "running"


# --- 2. Bounded early retry after a restart --------------------------------

@pytest.mark.asyncio
async def test_interrupted_run_is_retried_on_the_next_tick(quiet, monkeypatch):
    monkeypatch.setattr(settings, "MONITOR_RESTART_MAX_RETRIES", 2)
    suffix = uuid.uuid4().hex[:8]
    monitor_id = await _seed(suffix, runs=[("running", None, settings.MONITOR_RUN_TIMEOUT_S + 600)])
    await job_reconciliation._sweep_monitor_runs()
    monitor = await _monitor(monitor_id)
    assert monitor.next_run_at <= _now()
    assert any("retried within a few minutes" in body for _m, _t, body in quiet)


@pytest.mark.asyncio
async def test_a_monitor_that_keeps_dying_waits_for_its_cadence(quiet, monkeypatch):
    monkeypatch.setattr(settings, "MONITOR_RESTART_MAX_RETRIES", 2)
    suffix = uuid.uuid4().hex[:8]
    later = _now() + datetime.timedelta(hours=20)
    monitor_id = await _seed(suffix, next_run_at=later, runs=[
        ("failed", "service_restart", 7200),
        ("failed", "service_restart", 5400),
        ("running", None, settings.MONITOR_RUN_TIMEOUT_S + 600),
    ])
    await job_reconciliation._sweep_monitor_runs()
    monitor = await _monitor(monitor_id)
    assert monitor.next_run_at > _now() + datetime.timedelta(hours=19)
    assert any("next cadence" in body for _m, _t, body in quiet)


def test_restart_retry_rule():
    allowed = monitor_service.restart_retry_allowed
    restart = ("failed", "service_restart")
    assert allowed([restart], 2)
    assert allowed([restart, restart], 2)
    assert not allowed([restart, restart, restart], 2)
    assert allowed([restart, ("succeeded", None), restart, restart], 2)
    assert not allowed([("failed", "provider_error")], 2)
    assert not allowed([restart], 0)


# --- 3. Record budget -------------------------------------------------------

@pytest.mark.asyncio
async def test_platform_budget_leaves_due_monitors_unclaimed(monkeypatch):
    monkeypatch.setattr(settings, "METAPI_MONTHLY_RECORD_BUDGET", 0)  # nothing fits
    suffix = uuid.uuid4().hex[:8]
    due = _now() - datetime.timedelta(minutes=5)
    monitor_id = await _seed(suffix, next_run_at=due)

    out = await monitor_service.tick()
    assert out["dispatched"] == 0 and out.get("reason") == "platform_record_budget_reached"
    monitor = await _monitor(monitor_id)
    assert abs((monitor.next_run_at - due).total_seconds()) < 1  # not pushed a cadence
    assert monitor.last_run_at is None


@pytest.fixture
def spend_spy(monkeypatch):
    calls = {"charge": 0, "pipeline": 0}

    async def fake_assert(db, user, **_kw):
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one()
        return org, None

    async def fake_charge(**_kw):
        calls["charge"] += 1

    async def fake_pipeline(job_id, query, filters):
        calls["pipeline"] += 1

    monkeypatch.setattr(monitor_service, "assert_can_spend", fake_assert)
    monkeypatch.setattr(monitor_service, "charge", fake_charge)
    monkeypatch.setattr("app.services.discover_service.run_discovery_pipeline", fake_pipeline)
    return calls


@pytest.mark.asyncio
async def test_exhausted_budget_at_run_time_skips_without_charge(spend_spy, monkeypatch):
    monkeypatch.setattr(settings, "METAPI_MONTHLY_RECORD_BUDGET", 0)
    suffix = uuid.uuid4().hex[:8]
    monitor_id = await _seed(suffix)

    await monitor_service._run_monitor(monitor_id)

    assert spend_spy == {"charge": 0, "pipeline": 0}
    (run,) = await _run_rows(monitor_id)
    assert run.status == "skipped" and run.skipped_reason == "platform_record_budget_reached"


@pytest.mark.asyncio
async def test_workspace_budget_at_run_time_skips_without_charge(spend_spy, monkeypatch):
    from app.services import provider_budget

    async def workspace_full(db, org_id, provider="metapi"):
        return provider_budget.WORKSPACE_RECORD_BUDGET

    monkeypatch.setattr(provider_budget, "record_refusal", workspace_full)
    suffix = uuid.uuid4().hex[:8]
    monitor_id = await _seed(suffix)

    await monitor_service._run_monitor(monitor_id)

    assert spend_spy == {"charge": 0, "pipeline": 0}
    (run,) = await _run_rows(monitor_id)
    assert run.status == "skipped" and run.skipped_reason == "workspace_record_budget_reached"


# --- 4. Full lifecycle with a stubbed provider -------------------------------

ADS = {
    "a": ("Summer sale", "Up to 50% off everything", "Shop now", "a.example"),
    "b": ("Free shipping", "Order today, free delivery", "Order", "b.example"),
    "c": ("New arrivals", "Fresh styles this week", "Browse", "c.example"),
    "d": ("Gift guide", "Gifts for everyone", "Learn more", "d.example"),
}


@pytest.mark.asyncio
async def test_full_monitor_lifecycle_with_a_stubbed_provider(quiet, monkeypatch):
    plan = iter([["a", "b", "c"], ["a", "b", "c", "d"], ["a", "b", "d"], ["a", "b", "d"]])
    calls = {"charge": 0}

    async def fake_assert(db, user, **_kw):
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one()
        return org, None

    async def fake_charge(**_kw):
        calls["charge"] += 1

    async def fake_pipeline(job_id, query, filters):
        keys = next(plan)
        async with async_session_maker() as db:
            for k in keys:
                h, body, cta, domain = ADS[k]
                db.add(Creative(job_id=job_id, brand_id="acme", brand_name="Acme", platform="meta", format="image",
                                headline=h, body=body, cta=cta, landing_domain=domain))
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            job.status = "succeeded"
            job.record_count = len(keys)
            await db.commit()

    monkeypatch.setattr(monitor_service, "assert_can_spend", fake_assert)
    monkeypatch.setattr(monitor_service, "charge", fake_charge)
    monkeypatch.setattr("app.services.discover_service.run_discovery_pipeline", fake_pipeline)
    monkeypatch.setattr(settings, "MONITOR_MISS_THRESHOLD", 2)

    suffix = uuid.uuid4().hex[:8]
    monitor_id = await _seed(suffix)

    async def run_once():
        await monitor_service._run_monitor(monitor_id)
        return (await _run_rows(monitor_id))[0]

    baseline = await run_once()
    assert baseline.status == "succeeded" and baseline.is_baseline and baseline.new_count == 0

    second = await run_once()
    assert second.status == "succeeded" and not second.is_baseline
    assert (second.new_count, second.killed_count) == (1, 0)

    third = await run_once()  # "c" missing once: kept, missed_runs = 1
    assert third.killed_count == 0

    fourth = await run_once()  # "c" missing twice: killed
    assert fourth.killed_count == 1

    async with async_session_maker() as db:
        rows = (await db.execute(select(MonitorCreative).where(MonitorCreative.monitor_id == monitor_id))).scalars().all()
    by_headline = {r.headline: r for r in rows}
    assert by_headline["New arrivals"].status != "active"
    assert all(by_headline[h].status == "active" for h in ("Summer sale", "Free shipping", "Gift guide"))
    assert calls["charge"] == 4

    async with async_session_maker() as db:
        assert await db.scalar(select(func.count(MonitorRun.id)).where(MonitorRun.monitor_id == monitor_id)) == 4
