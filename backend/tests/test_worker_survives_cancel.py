"""Cancelling one search must never kill the embedded worker (no database needed).

Seen in production: the user pressed Cancel on a running search, a CancelledError from the search's
own inner task reached the worker loop, the loop treated it as a shutdown and exited, and every later
search stayed "Queued" until the service restarted."""
import asyncio

import pytest

from app.services import embedded_worker, job_runner


@pytest.mark.asyncio
async def test_inner_cancel_is_not_an_outer_cancel():
    async def inner_cancelled():
        inner = asyncio.create_task(asyncio.sleep(10))
        inner.cancel()
        try:
            await inner
        except asyncio.CancelledError:
            return job_runner.outer_cancel_requested()  # raised by the inner task only

    assert await inner_cancelled() is False


@pytest.mark.asyncio
async def test_real_shutdown_cancel_is_detected():
    seen = {}

    async def worker():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            seen["outer"] = job_runner.outer_cancel_requested()
            raise

    task = asyncio.create_task(worker())
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert seen["outer"] is True


@pytest.mark.asyncio
async def test_loop_keeps_polling_after_a_search_is_cancelled(monkeypatch):
    calls = {"claims": 0, "executed": []}

    async def fake_reconcile():
        return None

    async def fake_loop():
        await asyncio.sleep(3600)

    async def claim(owner):
        calls["claims"] += 1
        return "w1" if calls["claims"] == 1 else None

    async def execute(work_id, owner):
        calls["executed"].append(work_id)
        raise asyncio.CancelledError()  # what a cancelled search used to leak into the loop

    import app.services.job_reconciliation as rec
    import app.services.work_outbox as ob
    monkeypatch.setattr(rec, "reconcile_once", fake_reconcile)
    monkeypatch.setattr(rec, "reconciliation_loop", fake_loop)
    monkeypatch.setattr(ob, "claim_next_work_item", claim)
    monkeypatch.setattr(ob, "execute_work_item", execute)
    monkeypatch.setattr(job_runner, "monitor_scheduler_loop", lambda stop: fake_loop())

    stop = asyncio.Event()
    task = asyncio.create_task(job_runner.run_jobs(stop, "t", poll_interval_s=0.01))
    await asyncio.sleep(0.15)
    assert not task.done(), "the worker loop died after a cancelled search"
    assert calls["executed"] == ["w1"] and calls["claims"] > 2
    stop.set()
    await asyncio.wait_for(task, 2)


@pytest.mark.asyncio
async def test_a_dead_embedded_worker_is_restarted(monkeypatch):
    monkeypatch.setattr(embedded_worker.settings, "EMBEDDED_WORKER_ENABLED", True)
    started = []

    async def fake_run_jobs(stop, worker_id, poll_interval_s=2.0):
        started.append(worker_id)
        await stop.wait()

    monkeypatch.setattr(job_runner, "run_jobs", fake_run_jobs)
    monkeypatch.setattr(embedded_worker, "_task", None)
    assert await embedded_worker.ensure_running() is True
    await asyncio.sleep(0)
    assert started and embedded_worker.running()
    assert await embedded_worker.ensure_running() is True and len(started) == 1  # healthy: no second loop
    await embedded_worker.stop(timeout_s=2)
