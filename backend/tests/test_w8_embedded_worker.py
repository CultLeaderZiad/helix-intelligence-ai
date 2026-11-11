"""W8: the shared jobs loop (job_runner.run_jobs) and its embedded start/stop.

The real loop runs against the real work_items outbox and scrape_jobs rows.
Only the job body (work_outbox._dispatch) is controlled, so no provider is
called. Proves: completion, retry after an error, recovery after the process
stops mid-job (expired lease reclaimed by a new loop), and that the monitor
scheduler ticks inside the loop.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, update

from app.core.config import settings
from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.models.work_item import WorkItem
from app.services import embedded_worker, job_runner
from app.services import work_outbox as outbox


def now():
    return dt.datetime.now(dt.timezone.utc)


@pytest.fixture(autouse=True)
def fast_loop(monkeypatch):
    monkeypatch.setattr(settings, "MONITOR_SCHEDULER_INTERVAL_S", 0)

    async def _no_reconcile():
        return None

    async def _idle_reconcile_loop():
        await asyncio.Event().wait()

    import app.services.job_reconciliation as rec

    monkeypatch.setattr(rec, "reconcile_once", _no_reconcile)
    monkeypatch.setattr(rec, "reconciliation_loop", _idle_reconcile_loop)


@pytest_asyncio.fixture
async def queued_item():
    s = uuid.uuid4().hex[:10]
    user_id, org_id, job_id, item_id = f"ew_u_{s}", f"ew_o_{s}", f"ew_j_{s}", f"ew_w_{s}"
    async with worker_session_maker() as db:
        db.add(User(id=user_id, email=f"ew-{s}@example.com", password_hash="x", role="customer"))
        await db.flush()
        db.add(Organization(id=org_id, name="Embedded worker proof", owner_id=user_id, plan="pro"))
        await db.flush()
        db.add(ScrapeJob(id=job_id, org_id=org_id, query="test", status="queued", created_at=now(),
                         deadline_at=now() + dt.timedelta(minutes=5)))
        db.add(WorkItem(id=item_id, org_id=org_id, user_id=user_id, kind="discover", job_id=job_id,
                        payload={"query": "test"}, idempotency_key=item_id, status="queued",
                        attempt_count=0, max_attempts=3, available_at=now()))
        await db.commit()
    yield {"item": item_id, "job": job_id, "org": org_id}
    async with worker_session_maker() as db:
        await db.execute(delete(WorkItem).where(WorkItem.org_id == org_id))
        await db.execute(delete(ScrapeJob).where(ScrapeJob.org_id == org_id))
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _item(item_id):
    async with worker_session_maker() as db:
        return await db.get(WorkItem, item_id)


async def _until(predicate, timeout=30.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(0.2)
    return False


async def _run(worker_id):
    stop = asyncio.Event()
    task = asyncio.create_task(job_runner.run_jobs(stop, worker_id, poll_interval_s=0.2))
    return stop, task


async def _stop(stop, task):
    stop.set()
    await asyncio.wait_for(task, timeout=20)


@pytest.mark.asyncio
async def test_loop_claims_and_completes_a_queued_job(queued_item, monkeypatch):
    calls = []

    async def body(kind, job_id, *args):
        calls.append(job_id)

    monkeypatch.setattr(outbox, "_dispatch", body)
    stop, task = await _run("proof-complete")
    try:
        assert await _until(lambda: _status_is(queued_item["item"], "succeeded"))
    finally:
        await _stop(stop, task)
    assert calls == [queued_item["job"]]
    assert (await _item(queued_item["item"])).attempt_count == 1


async def _status_is(item_id, status):
    item = await _item(item_id)
    return item is not None and item.status == status


@pytest.mark.asyncio
async def test_an_error_is_retried_with_backoff_then_completes(queued_item, monkeypatch):
    attempts = []

    async def flaky(kind, job_id, *args):
        attempts.append(job_id)
        if len(attempts) == 1:
            raise RuntimeError("transient provider error")

    monkeypatch.setattr(outbox, "_dispatch", flaky)
    stop, task = await _run("proof-retry")
    try:
        assert await _until(lambda: _requeued(queued_item["item"]))
        # Skip the real backoff (2 s) so the test stays fast.
        async with worker_session_maker() as db:
            await db.execute(update(WorkItem).where(WorkItem.id == queued_item["item"]).values(available_at=now()))
            await db.commit()
        assert await _until(lambda: _status_is(queued_item["item"], "succeeded"))
    finally:
        await _stop(stop, task)
    item = await _item(queued_item["item"])
    assert len(attempts) == 2 and item.attempt_count == 2


async def _requeued(item_id):
    item = await _item(item_id)
    return item.status == "queued" and int(item.attempt_count or 0) == 1 and item.last_error


@pytest.mark.asyncio
async def test_a_job_left_by_a_stopped_process_is_reclaimed_and_finished(queued_item, monkeypatch):
    started = asyncio.Event()

    async def hangs(kind, job_id, *args):
        started.set()
        await asyncio.Event().wait()  # never finishes: simulates the process dying mid-job

    monkeypatch.setattr(outbox, "_dispatch", hangs)
    stop, task = await _run("proof-dead-process")
    await asyncio.wait_for(started.wait(), timeout=20)
    task.cancel()  # the process goes away; the row keeps its lease
    await asyncio.gather(task, return_exceptions=True)
    item = await _item(queued_item["item"])
    assert item.status == "running" and item.lease_owner == "proof-dead-process"

    # The lease expires (a real host: lease_until passes), the next loop requeues it.
    async with worker_session_maker() as db:
        await db.execute(update(WorkItem).where(WorkItem.id == queued_item["item"]).values(
            lease_until=now() - dt.timedelta(seconds=1)))
        await db.commit()
    assert await outbox.requeue_expired_leases() >= 1
    async with worker_session_maker() as db:
        await db.execute(update(WorkItem).where(WorkItem.id == queued_item["item"]).values(available_at=now()))
        await db.commit()

    done = []

    async def finishes(kind, job_id, *args):
        done.append(job_id)

    monkeypatch.setattr(outbox, "_dispatch", finishes)
    stop2, task2 = await _run("proof-restarted")
    try:
        assert await _until(lambda: _status_is(queued_item["item"], "succeeded"))
    finally:
        await _stop(stop2, task2)
    assert done == [queued_item["job"]]
    assert (await _item(queued_item["item"])).attempt_count == 2


@pytest.mark.asyncio
async def test_monitor_scheduler_ticks_inside_the_loop(monkeypatch):
    ticks = []

    async def tick():
        ticks.append(1)
        return {"dispatched": 0}

    import app.services.monitor_service as monitors

    monkeypatch.setattr(monitors, "tick", tick)
    monkeypatch.setattr(settings, "MONITOR_SCHEDULER_INTERVAL_S", 1)

    async def no_work(owner):
        return None

    monkeypatch.setattr(outbox, "claim_next_work_item", no_work)
    stop, task = await _run("proof-scheduler")
    try:
        assert await _until(lambda: _at_least(ticks, 2), timeout=10)
    finally:
        await _stop(stop, task)


async def _at_least(items, n):
    return len(items) >= n


@pytest.mark.asyncio
async def test_embedded_worker_starts_only_when_enabled_and_stops_cleanly(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDED_WORKER_ENABLED", False)
    assert await embedded_worker.start() is False
    assert not embedded_worker.running()

    async def no_work(owner):
        return None

    monkeypatch.setattr(outbox, "claim_next_work_item", no_work)
    monkeypatch.setattr(settings, "EMBEDDED_WORKER_ENABLED", True)
    assert await embedded_worker.start() is True
    assert embedded_worker.running()
    assert await embedded_worker.start() is True  # idempotent
    await embedded_worker.stop(timeout_s=10)
    assert not embedded_worker.running()


@pytest.mark.asyncio
async def test_health_reports_worker_state_without_secrets(monkeypatch):
    from app.api.routers import health

    monkeypatch.setattr(settings, "EMBEDDED_WORKER_ENABLED", False)
    assert health._worker_status() == {"mode": "external_or_disabled", "running": None, "last_poll_seconds_ago": None}

    async def no_work(owner):
        return None

    monkeypatch.setattr(outbox, "claim_next_work_item", no_work)
    monkeypatch.setattr(settings, "EMBEDDED_WORKER_ENABLED", True)
    await embedded_worker.start()
    try:
        assert await _until(lambda: _polled(), timeout=10)
        state = health._worker_status()
        assert state["mode"] == "embedded" and state["running"] is True
        assert 0 <= state["last_poll_seconds_ago"] <= 5
    finally:
        await embedded_worker.stop(timeout_s=10)


async def _polled():
    return job_runner.seconds_since_last_poll() is not None
