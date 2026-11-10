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
from app.core.observability import quiet_http_client_logs  # noqa: E402

quiet_http_client_logs()
logger = logging.getLogger("helix.worker")

BOOT_ID = f"worker:{uuid.uuid4().hex}"
POLL_INTERVAL_S = float(os.environ.get("WORKER_POLL_INTERVAL_S", "2"))
_stop = asyncio.Event()


async def _check_rls_role() -> None:
    from app.core.rls_role import assert_rls_role
    from app.db.session import worker_engine

    async with worker_engine.connect() as conn:
        await assert_rls_role(conn)


async def _worker_loop() -> None:
    from app.services.job_runner import run_jobs

    await run_jobs(_stop, BOOT_ID, POLL_INTERVAL_S)


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
