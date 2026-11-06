"""Helix jobs worker: runs durable work items and job reconciliation.

It claims rows from the Postgres ``work_items`` outbox (Discover searches and
Monitor runs), executes them with lease renewal and fencing, and sweeps stale
jobs every 60 s. It needs no browser and no scraping framework.

Run on a host:
    cd backend && python workers/jobs/worker.py

Run in Docker (build from backend/):
    docker build -f workers/jobs/Dockerfile -t helix-jobs-worker .
    docker run --env-file .env helix-jobs-worker

Environment:
    DATABASE_URL   the restricted worker login (helix_worker_login)
    SECRET_KEY     same value as the API
    WORKER_POLL_INTERVAL_S (optional, default 2)
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import uuid
from pathlib import Path

# Make the backend package importable when launched as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("helix.worker")

BOOT_ID = f"worker:{uuid.uuid4().hex}"
POLL_INTERVAL_S = float(os.environ.get("WORKER_POLL_INTERVAL_S", "2"))
_stop = asyncio.Event()


async def _check_rls_role() -> None:
    from app.core.rls_role import assert_rls_role
    from app.db.session import worker_engine

    async with worker_engine.connect() as conn:
        await assert_rls_role(conn)


async def _monitor_scheduler_loop() -> None:
    """Enqueue due monitors on a timer; the claim is SKIP LOCKED, so an
    external cron calling /api/monitors/tick as well is harmless."""
    from app.core.config import settings
    from app.services.monitor_service import tick

    interval = int(settings.MONITOR_SCHEDULER_INTERVAL_S)
    if interval <= 0:
        logger.info("in-worker monitor scheduler disabled")
        return
    while not _stop.is_set():
        try:
            result = await tick()
            if result.get("dispatched"):
                logger.info("monitor scheduler dispatched %s", result["dispatched"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("monitor scheduler tick failed: %s", exc)
        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def _worker_loop() -> None:
    from app.services.job_reconciliation import reconcile_once, reconciliation_loop
    from app.services.work_outbox import claim_next_work_item, execute_work_item

    await reconcile_once()
    reconciler = asyncio.create_task(reconciliation_loop())
    scheduler = asyncio.create_task(_monitor_scheduler_loop())
    try:
        while not _stop.is_set():
            try:
                work_id = await claim_next_work_item(BOOT_ID)
                if work_id:
                    logger.info("claimed work item %s", work_id)
                    await execute_work_item(work_id, BOOT_ID)
                    continue
                try:
                    await asyncio.wait_for(_stop.wait(), timeout=POLL_INTERVAL_S)
                except asyncio.TimeoutError:
                    pass
            except Exception as exc:  # keep the loop alive; the item's lease handles retries
                logger.exception("worker loop error: %s", exc)
                await asyncio.sleep(POLL_INTERVAL_S)
    finally:
        reconciler.cancel()
        scheduler.cancel()
        await asyncio.gather(reconciler, scheduler, return_exceptions=True)


async def _main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _stop.set)
        except NotImplementedError:  # Windows: rely on KeyboardInterrupt
            pass
    await _check_rls_role()
    logger.info("worker ready (%s)", BOOT_ID)
    await _worker_loop()


def main() -> None:
    for var in ("DATABASE_URL", "SECRET_KEY"):
        if not os.environ.get(var):
            print(f"FATAL: {var} environment variable is required", file=sys.stderr)
            sys.exit(1)
    try:
        asyncio.run(_main())
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    logger.info("worker stopped")


if __name__ == "__main__":
    main()
