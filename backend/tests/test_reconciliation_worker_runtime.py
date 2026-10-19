"""Worker-only maintenance and monitor lookup ordering contracts (no live DB)."""
from __future__ import annotations

import asyncio
import datetime
import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.tenancy import current_tenant
from app.services import job_reconciliation as reconciliation
from workers.scrapling import worker


def session_factory(db):
    @asynccontextmanager
    async def factory():
        yield db
    return factory


def test_api_lifespan_has_no_maintenance():
    source = (Path(__file__).resolve().parents[1] / "app/main.py").read_text()
    lifespan = source.split("async def lifespan", 1)[1].split("app = FastAPI", 1)[0]
    assert "reconcil" not in lifespan
    assert "apply_maintenance_context" not in source


def test_reconciliation_uses_only_worker_sessions():
    source = inspect.getsource(reconciliation)
    assert "async_session_maker" not in source
    assert "worker_session_maker" in source


@pytest.mark.asyncio
async def test_failed_scrape_refunds_use_last_activity_in_last_24_hours():
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    db.execute.return_value = result
    with patch.object(reconciliation, "worker_session_maker", session_factory(db)), \
         patch.object(reconciliation, "apply_maintenance_context", AsyncMock()):
        assert await reconciliation._sweep_unrefunded_failed_jobs() == []
    statement, params = db.execute.await_args.args
    assert "COALESCE(sj.completed_at, sj.heartbeat_at, sj.created_at) >= :refund_cutoff" in str(statement)
    age = datetime.datetime.now(datetime.timezone.utc) - params["refund_cutoff"]
    assert 24 * 3600 <= age.total_seconds() < 24 * 3600 + 2


@pytest.mark.asyncio
async def test_refunds_use_worker_sessions_with_explicit_tenant_scope():
    db = AsyncMock()
    refunds = []
    session_orgs = []

    @asynccontextmanager
    async def worker_session():
        session_orgs.append(current_tenant().org_ids)
        yield db

    async def refund(session, org_id, _credits, _reason, job_id):
        assert session is db
        ctx = current_tenant()
        assert ctx.org_ids == [org_id]
        assert ctx.platform_admin is False
        refunds.append(job_id)

    sweep = AsyncMock(side_effect=[
        [{"id": "discover", "org_id": "org-discover"}],
        [],
        [{"id": "scout", "org_id": "org-scout", "credits_used": 2}],
        [{"id": "maps", "org_id": "org-maps", "credits_used": 3}],
        [{"id": "leadgen", "org_id": "org-leadgen", "credits_used": 4}],
    ])
    with patch.object(reconciliation, "worker_session_maker", worker_session), \
         patch.object(reconciliation, "_sweep_table", sweep), \
         patch.object(reconciliation, "_sweep_unrefunded_failed_jobs", AsyncMock(return_value=[])), \
         patch.object(reconciliation, "_sweep_monitor_runs", AsyncMock(return_value=0)), \
         patch.object(reconciliation, "refund", side_effect=refund), \
         patch("app.services.work_outbox.requeue_expired_leases", AsyncMock(return_value=0)):
        swept = await reconciliation.reconcile_once()
    assert refunds == ["discover", "scout", "maps", "leadgen"]
    assert session_orgs == [["org-discover"], ["org-scout"], ["org-maps"], ["org-leadgen"]]
    assert swept["refunded"] == 4
    assert sweep.await_args_list[0].kwargs["extra_update_clauses"] == "completed_at = now()"


@pytest.mark.asyncio
async def test_sweep_binds_selected_orgs_before_marking_rows_failed():
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"
    selected = MagicMock()
    selected.mappings.return_value.all.return_value = [
        {"id": "job-1", "org_id": "org-1"},
        {"id": "job-2", "org_id": "org-2"},
    ]
    db.execute.return_value = selected
    bound = []

    async def bind_tenant(session):
        assert session is db
        bound.append(current_tenant().org_ids)

    with patch.object(reconciliation, "worker_session_maker", session_factory(db)), \
         patch.object(reconciliation, "apply_maintenance_context", AsyncMock()), \
         patch.object(reconciliation, "apply_tenant_context", side_effect=bind_tenant, create=True):
        rows = await reconciliation._sweep_table("media_jobs", ("running",), "error_message", "interrupted")
    assert len(rows) == 2
    assert "SELECT id, org_id FROM media_jobs" in str(db.execute.await_args_list[0].args[0])
    assert bound == [["org-1", "org-2"]]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_monitor_org_lookup_precedes_failure_and_survives_commit():
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"
    events = []

    async def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock()
        if "SELECT mr.id, mr.monitor_id" in sql:
            assert "FOR UPDATE OF mr SKIP LOCKED" in sql
            result.mappings.return_value.all.return_value = [{"id": "run-1", "monitor_id": "monitor-1"}]
        elif "SELECT org_id FROM monitors" in sql:
            events.append("lookup")
            result.scalar_one_or_none.return_value = "org-1"
        elif "UPDATE monitor_runs" in sql:
            assert current_tenant().org_ids == ["org-1"]
            events.append("fail")
            result.scalar_one_or_none.return_value = "monitor-1"
        else:
            raise AssertionError(sql)
        return result

    async def commit():
        events.append("commit")

    async def notify(monitor_id):
        events.append("notify")
        assert monitor_id == "monitor-1"
        assert current_tenant().org_ids == ["org-1"]

    db.execute.side_effect = execute
    db.commit.side_effect = commit
    with patch.object(reconciliation, "worker_session_maker", session_factory(db)), \
         patch.object(reconciliation, "apply_maintenance_context", AsyncMock()), \
         patch.object(reconciliation, "apply_tenant_context", AsyncMock(), create=True), \
         patch.object(reconciliation, "apply_monitor_maintenance_lookup_context", AsyncMock()), \
         patch("app.services.monitor_service.notify_run_interrupted", side_effect=notify):
        assert await reconciliation._sweep_monitor_runs() == 1
    assert events == ["lookup", "fail", "commit", "notify"]


@pytest.mark.asyncio
async def test_worker_starts_and_cancels_periodic_maintenance():
    events = []
    periodic_started = asyncio.Event()

    async def startup():
        events.append("startup")

    async def periodic():
        events.append("periodic")
        periodic_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            events.append("cancelled")

    async def claim(_boot_id):
        await periodic_started.wait()
        events.append("claim")
        worker._stop.set()
        return None

    worker._stop.clear()
    try:
        with patch.object(reconciliation, "reconcile_once", side_effect=startup), \
             patch.object(reconciliation, "reconciliation_loop", side_effect=periodic), \
             patch("app.services.work_outbox.claim_next_work_item", side_effect=claim), \
             patch.object(worker, "_claim_next_job_async", AsyncMock(return_value=None)), \
             patch.object(worker, "POLL_INTERVAL_S", 0):
            await worker._worker_loop(AsyncMock())
        assert events == ["startup", "periodic", "claim", "cancelled"]
    finally:
        worker._stop.clear()
