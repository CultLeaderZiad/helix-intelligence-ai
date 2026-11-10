"""The jobs worker loop, shared by the standalone worker and the API process.

``run_jobs(stop, worker_id)`` claims durable work items (Discover searches
and monitor runs) from the ``work_items`` outbox, executes them with lease
renewal and fencing, sweeps stale jobs, and ticks the monitor scheduler. It
returns when ``stop`` is set.

Two ways to run it:

* Standalone (``python workers/jobs/worker.py``): its own process, connected
  as the worker login.
* Embedded (``EMBEDDED_WORKER_ENABLED=true``): a background task inside the
  API process, for free hosting with a single service. The API's database
  login must then also be a member of ``helix_worker``
  (``GRANT helix_worker TO <api login>``). Worker-only rows stay protected:
  the claim policies also require the ``helix.worker_claim`` setting, which
  only this loop sets, never a request handler.

Durability is the same either way. A job whose process dies keeps an expired
lease; the next running loop requeues and reclaims it, and stale completions
from the old lease are fenced out. What the embedded mode cannot do is run
while the host is asleep: see docs/w8/free-worker.md.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("helix.worker")

# Monotonic time of the loop's last poll. /api/health reads it to prove the
# loop is cycling, not just started.
last_poll_monotonic: Optional[float] = None


def seconds_since_last_poll() -> Optional[int]:
    if last_poll_monotonic is None:
        return None
    return int(time.monotonic() - last_poll_monotonic)


async def _wait(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


async def monitor_scheduler_loop(stop: asyncio.Event) -> None:
    """Enqueue due monitors on a timer. The claim is SKIP LOCKED, so an external
    cron calling /api/monitors/tick at the same time is harmless."""
    from app.core.config import settings
    from app.services.monitor_service import tick

    interval = int(settings.MONITOR_SCHEDULER_INTERVAL_S)
    if interval <= 0:
        logger.info("in-worker monitor scheduler disabled")
        return
    while not stop.is_set():
        try:
            result = await tick()
            if result.get("dispatched"):
                logger.info("monitor scheduler dispatched %s", result["dispatched"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("monitor scheduler tick failed: %s", exc)
        await _wait(stop, interval)


async def run_jobs(stop: asyncio.Event, worker_id: str, poll_interval_s: float = 2.0) -> None:
    global last_poll_monotonic
    from app.services.job_reconciliation import reconcile_once, reconciliation_loop
    from app.services.work_outbox import claim_next_work_item, execute_work_item

    try:
        await reconcile_once()
    except Exception as exc:  # a bad sweep must not stop job execution
        logger.exception("initial reconciliation failed: %s", exc)
    reconciler = asyncio.create_task(reconciliation_loop())
    scheduler = asyncio.create_task(monitor_scheduler_loop(stop))
    try:
        while not stop.is_set():
            last_poll_monotonic = time.monotonic()
            try:
                work_id = await claim_next_work_item(worker_id)
                if work_id:
                    logger.info("claimed work item %s", work_id)
                    await execute_work_item(work_id, worker_id)
                    continue
                await _wait(stop, poll_interval_s)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep the loop alive; the item's lease handles retries
                logger.exception("worker loop error: %s", exc)
                await _wait(stop, poll_interval_s)
    finally:
        reconciler.cancel()
        scheduler.cancel()
        await asyncio.gather(reconciler, scheduler, return_exceptions=True)
