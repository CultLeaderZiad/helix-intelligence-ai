"""Real loopback PostgreSQL proofs; provider coroutines are controlled, never called."""
import asyncio
import datetime as dt
import uuid
from unittest.mock import AsyncMock

import pytest
import httpx
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.models.work_item import WorkItem
from app.services import discover_service as discover
from app.services import job_heartbeat, work_outbox as outbox


def now():
    return dt.datetime.now(dt.timezone.utc)


@pytest_asyncio.fixture
async def job(monkeypatch):
    url = make_url(settings.async_database_url)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or not ("w5" in (url.database or "") or url.database == "helix_test_db"):
        pytest.skip("W5 tests require an explicitly configured disposable loopback database")
    for module in (discover, job_heartbeat, outbox):
        monkeypatch.setattr(module, "async_session_maker", worker_session_maker)
    monkeypatch.setattr(discover, "refund", AsyncMock())
    suffix = uuid.uuid4().hex
    user_id, org_id, job_id = [f"w5_{name}_{suffix}" for name in ("user", "org", "job")]
    async with worker_session_maker() as db:
        db.add(User(id=user_id, email=f"{suffix}@example.test", password_hash="test-only", role="customer"))
        await db.flush()
        db.add(Organization(id=org_id, name="Disposable W5 proof", owner_id=user_id, plan="pro"))
        await db.flush()
        db.add(ScrapeJob(id=job_id, org_id=org_id, query="test", status="queued", created_at=now(), deadline_at=now() + dt.timedelta(seconds=30)))
        await db.commit()
    yield {"id": job_id, "org": org_id, "user": user_id}
    async with worker_session_maker() as db:
        await db.execute(delete(WorkItem).where(WorkItem.org_id == org_id))
        await db.execute(delete(ScrapeJob).where(ScrapeJob.org_id == org_id))
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def state(job):
    async with worker_session_maker() as db:
        return (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job["id"]))).scalar_one()


@pytest.mark.asyncio
async def test_cancel_mid_provider_call_stops_task_and_cannot_cross_tenants(job, monkeypatch):
    started, stopped = asyncio.Event(), asyncio.Event()
    async def provider(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
    monkeypatch.setattr(discover, "_run_discovery_pipeline", provider)
    task = asyncio.create_task(discover.run_discovery_pipeline(job["id"], "test"))
    await asyncio.wait_for(started.wait(), 3)
    try:
        async with worker_session_maker() as db:
            with pytest.raises(HTTPException) as error:
                await discover.cancel_search(db, job["id"], user_org_ids=["other-tenant"])
            assert error.value.status_code == 404
        async with worker_session_maker() as db:
            response = await discover.cancel_search(db, job["id"], user_org_ids=[job["org"]])
        assert response.status == "cancelled"
        await asyncio.wait_for(stopped.wait(), 3)
        await asyncio.gather(task, return_exceptions=True)
        assert (await state(job)).status == "cancelled"
        assert not await discover._finalize_discovery_job(job["id"], status="succeeded")
        assert discover.refund.await_count == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_server_deadline_aborts_hung_provider_and_finalizes_once(job, monkeypatch):
    started, stopped = asyncio.Event(), asyncio.Event()
    async with worker_session_maker() as db:
        await db.execute(update(ScrapeJob).where(ScrapeJob.id == job["id"]).values(deadline_at=now() + dt.timedelta(seconds=5)))
        await db.commit()
    async def hung_provider(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
    monkeypatch.setattr(discover, "_run_discovery_pipeline", hung_provider)
    task = asyncio.create_task(discover.run_discovery_pipeline(job["id"], "test"))
    await asyncio.wait_for(started.wait(), 4)
    await asyncio.wait_for(task, 6)
    assert stopped.is_set()
    result = await state(job)
    assert result.status == "timed_out" and result.failure_kind == "deadline"
    assert result.completed_at is not None
    assert not await discover._finalize_discovery_job(job["id"], status="failed", refund_reason="duplicate")
    assert discover.refund.await_count == 1


@pytest.mark.asyncio
async def test_expired_queued_job_becomes_terminal_without_worker(job):
    async with worker_session_maker() as db:
        await db.execute(update(ScrapeJob).where(ScrapeJob.id == job["id"]).values(deadline_at=now() - dt.timedelta(seconds=1)))
        await db.commit()
        result = await discover.get_job_status(db, job["id"], user_org_ids=[job["org"]])
    assert result.status == "timed_out"
    assert discover.refund.await_count == 1


@pytest.mark.asyncio
async def test_crash_reclaim_fences_stale_completion_and_duplicate_delivery(job, monkeypatch):
    item_id = f"work_{uuid.uuid4().hex}"
    async with worker_session_maker() as db:
        db.add(WorkItem(id=item_id, org_id=job["org"], user_id=job["user"], kind="discover", job_id=job["id"], payload={"query": "test"}, idempotency_key=item_id, status="running", attempt_count=1, max_attempts=3, lease_owner="dead-worker", lease_until=now()-dt.timedelta(seconds=1), available_at=now()))
        await db.commit()
    assert await outbox.requeue_expired_leases() >= 1
    async with worker_session_maker() as db:
        await db.execute(update(WorkItem).where(WorkItem.id == item_id).values(available_at=now()-dt.timedelta(seconds=1)))
        await db.commit()
    assert await outbox.claim_next_work_item("replacement") == item_id
    async with worker_session_maker() as db:
        item = await db.get(WorkItem, item_id)
        assert item.attempt_count == 2
        item.status = "running"
        await db.commit()
    assert not await discover._finalize_discovery_job(job["id"], status="succeeded", work_item_id=item_id, lease_owner="dead-worker", lease_generation=1)
    assert await discover._finalize_discovery_job(job["id"], status="succeeded", work_item_id=item_id, lease_owner="replacement", lease_generation=2)
    assert not await discover._finalize_discovery_job(job["id"], status="failed", work_item_id=item_id, lease_owner="replacement", lease_generation=2)
    assert (await state(job)).status == "succeeded"
    # A duplicate queue delivery is rejected before reaching the provider.
    dispatch = AsyncMock()
    monkeypatch.setattr(outbox, "_dispatch", dispatch)
    await outbox.execute_work_item(item_id, "dead-worker")
    dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_renews_owned_lease_and_blocks_reclaim(job):
    item_id = f"work_{uuid.uuid4().hex}"
    before = now()+dt.timedelta(seconds=1)
    async with worker_session_maker() as db:
        db.add(WorkItem(id=item_id, org_id=job["org"], user_id=job["user"], kind="discover", job_id=job["id"], payload={}, idempotency_key=item_id, status="running", attempt_count=1, max_attempts=3, lease_owner="live-worker", lease_until=before, available_at=now()))
        await db.commit()
    assert await outbox._renew_work_lease(item_id, "live-worker", 1, job["id"], "discover") is None
    async with worker_session_maker() as db:
        item = await db.get(WorkItem, item_id)
        assert item.lease_until > before
    await outbox.requeue_expired_leases()
    async with worker_session_maker() as db:
        assert (await db.get(WorkItem, item_id)).status == "running"


@pytest.mark.asyncio
async def test_provider_timeout_is_distinct_from_the_overall_deadline(job, monkeypatch):
    async def timed_out_provider(*args, **kwargs):
        raise httpx.ReadTimeout("private vendor detail must not escape")
    monkeypatch.setattr(discover, "_run_discovery_pipeline", timed_out_provider)
    await discover.run_discovery_pipeline(job["id"], "test")
    result = await state(job)
    assert result.status == "failed" and result.failure_kind == "provider_timeout"
    assert "private vendor" not in result.error_msg
    assert discover.refund.await_count == 1
