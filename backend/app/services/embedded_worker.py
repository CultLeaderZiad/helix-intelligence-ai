"""Start and stop the jobs worker inside the API process (EMBEDDED_WORKER_ENABLED)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("helix.worker")

_stop: Optional[asyncio.Event] = None
_task: Optional[asyncio.Task] = None
WORKER_ID = f"api-embedded:{uuid.uuid4().hex}"


def running() -> bool:
    return _task is not None and not _task.done()


async def start() -> bool:
    """Start the loop once. Returns True when it is running after the call."""
    global _stop, _task
    if not settings.EMBEDDED_WORKER_ENABLED:
        return False
    if running():
        return True
    from app.services.job_runner import run_jobs

    _stop = asyncio.Event()
    _task = asyncio.create_task(run_jobs(_stop, WORKER_ID), name="helix-embedded-worker")
    logger.info("embedded jobs worker started (%s)", WORKER_ID)
    return True


async def stop(timeout_s: float = 20.0) -> None:
    """Ask the loop to finish its current item, then cancel it if it overruns.
    A cancelled item keeps its lease and is reclaimed after it expires."""
    global _task
    if _task is None:
        return
    if _stop is not None:
        _stop.set()
    try:
        await asyncio.wait_for(_task, timeout=timeout_s)
    except asyncio.TimeoutError:
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
    except Exception as exc:
        logger.exception("embedded worker stopped with an error: %s", exc)
    _task = None
    logger.info("embedded jobs worker stopped")
