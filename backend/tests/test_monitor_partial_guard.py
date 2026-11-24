"""A partial scrape must not turn into a mass "ad stopped" report."""

from app.services.creative_fingerprint import CreativeSignature, PriorState, diff_run
from app.services.monitor_service import partial_guard_active


def _sig(n: int, content: str = "c") -> CreativeSignature:
    return CreativeSignature(identity=f"id{n}", content=f"{content}{n}", anchor="headline", headline=f"Ad {n}")


def _prior(n: int, missed: int = 0) -> PriorState:
    return PriorState(identity=f"id{n}", content=f"c{n}", status="active", missed_runs=missed)


def _known(count: int, missed: int = 0):
    return {f"id{n}": _prior(n, missed) for n in range(count)}


def test_a_run_with_far_fewer_ads_than_known_is_inconclusive():
    result = diff_run([_sig(n) for n in range(3)], _known(10))
    assert result.skipped_reason == "partial_result"
    assert result.total_events == 0
    assert result.killed == [] and result.pending_misses == []


def test_the_partial_guard_does_not_apply_to_small_monitors():
    # 5 tracked ads is below the minimum, so one absence of 2 is judged normally.
    result = diff_run([_sig(n) for n in range(3)], _known(5, missed=1))
    assert result.skipped_reason is None
    assert len(result.killed) == 2


def test_a_run_at_the_threshold_is_accepted():
    # 5 of 10 is exactly 50%: not below the ratio.
    result = diff_run([_sig(n) for n in range(5)], _known(10))
    assert result.skipped_reason is None


def test_guard_can_be_turned_off_by_the_caller():
    result = diff_run([_sig(n) for n in range(3)], _known(10, missed=1), partial_guard=False)
    assert result.skipped_reason is None
    assert len(result.killed) == 7


def test_baseline_and_empty_still_win_over_the_partial_check():
    assert diff_run([], _known(10)).skipped_reason == "empty_result"
    assert diff_run([_sig(1)], _known(10), is_baseline=True).skipped_reason == "baseline"


def test_dead_ads_do_not_count_toward_the_known_total():
    known = _known(10)
    for n in range(6):
        known[f"id{n}"].status = "gone"
    # 4 active ads remain, below the minimum, so the guard does not apply.
    assert diff_run([_sig(9)], known).skipped_reason is None


def test_guard_stays_on_until_the_streak_is_long_enough():
    assert partial_guard_active([], 3) is True
    assert partial_guard_active(["partial_result"], 3) is True
    assert partial_guard_active([None, "partial_result"], 3) is True
    assert partial_guard_active(["partial_result", "partial_result"], 3) is False
    assert partial_guard_active(["partial_result", None], 3) is True


def test_a_max_of_one_never_guards():
    assert partial_guard_active([], 1) is False


# ---------------------------------------------------------------------------
# End to end through _apply_diff against Postgres
# ---------------------------------------------------------------------------

import datetime
import uuid

import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.monitor import Monitor, MonitorCreative, MonitorEvent, MonitorRun
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import monitor_service


async def _seed(suffix: str, known: int, seen: int, earlier_partial_runs: int = 0):
    """A monitor tracking ``known`` ads whose next run returns ``seen`` of them."""
    from app.services.creative_fingerprint import signatures_for_run

    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"partial-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Partial", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        monitor = Monitor(id=f"m_{suffix}", org_id=org.id, user_id=user.id, name="M", query="q")
        monitor.baseline_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(monitor)
        await db.flush()

        job = ScrapeJob(id=f"j_{suffix}", org_id=org.id, query="q")
        db.add(job)
        await db.flush()

        all_creatives = [
            Creative(
                id=f"c{n}_{suffix}", job_id=job.id, brand_id="b", platform="meta", format="image",
                headline=f"Headline number {n}", body=f"Body {n}",
            )
            for n in range(known)
        ]
        # What the monitor already remembers: every ad, active.
        for sig, creative in zip(signatures_for_run(all_creatives), all_creatives):
            db.add(MonitorCreative(
                monitor_id=monitor.id, identity_hash=sig.identity, content_hash=sig.content,
                status="active", missed_runs=0, headline=creative.headline,
            ))
        # This run only returns the first ``seen``.
        for creative in all_creatives[:seen]:
            db.add(creative)
        for i in range(earlier_partial_runs):
            db.add(MonitorRun(
                id=f"old{i}_{suffix}", monitor_id=monitor.id, status="succeeded", skipped_reason="partial_result",
                started_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=10 - i),
            ))
        db.add(MonitorRun(id=f"r_{suffix}", monitor_id=monitor.id, job_id=job.id, status="running"))
        await db.commit()
    return monitor.id, job.id, f"r_{suffix}"


async def _state(monitor_id: str, run_id: str):
    async with async_session_maker() as db:
        rows = (await db.execute(select(MonitorCreative).where(MonitorCreative.monitor_id == monitor_id))).scalars().all()
        events = (await db.execute(select(MonitorEvent).where(MonitorEvent.monitor_id == monitor_id))).scalars().all()
        run = (await db.execute(select(MonitorRun).where(MonitorRun.id == run_id))).scalar_one()
    return rows, events, run


@pytest.mark.asyncio
async def test_a_partial_run_changes_nothing():
    suffix = uuid.uuid4().hex[:8]
    monitor_id, job_id, run_id = await _seed(suffix, known=10, seen=2)

    await monitor_service._apply_diff(monitor_id, run_id, job_id, False)

    rows, events, run = await _state(monitor_id, run_id)
    assert events == []
    assert all(r.status == "active" and (r.missed_runs or 0) == 0 for r in rows)
    assert run.status == "succeeded"
    assert run.skipped_reason == "partial_result"
    assert run.killed_count == 0


@pytest.mark.asyncio
async def test_after_three_partial_runs_the_smaller_catalogue_is_accepted():
    suffix = uuid.uuid4().hex[:8]
    # Two earlier partial runs, so this is the third in a row. Pre-load one miss
    # so the 8 absent ads cross the miss threshold on this run.
    monitor_id, job_id, run_id = await _seed(suffix, known=10, seen=2, earlier_partial_runs=2)
    async with async_session_maker() as db:
        for row in (await db.execute(select(MonitorCreative).where(MonitorCreative.monitor_id == monitor_id))).scalars():
            row.missed_runs = 1
        await db.commit()

    await monitor_service._apply_diff(monitor_id, run_id, job_id, False)

    rows, events, run = await _state(monitor_id, run_id)
    assert run.skipped_reason is None
    assert sorted(e.type for e in events).count("killed_ad") == 8
