"""Liveness signal for in-process background jobs.

A job that is genuinely running writes a timestamp every few seconds. That
turns "is this job dead?" into "has it been silent?", which is accurate
regardless of how long the job legitimately takes.

Without this, the only available signal is the job's total age, which forces a
threshold above the slowest legitimate run. Real production data for this app
puts discovery p95 at 5.3 minutes and max at 5.4 minutes, so an age-based
threshold has to sit around ten minutes -- meaning a user whose job died in the
first second still waits ten minutes to find out. Silence-based detection
brings that down to two minutes without any risk to slow-but-healthy jobs.
"""

import asyncio
import contextlib
import datetime
import logging
from typing import Literal

from sqlalchemy import text

from app.core.config import settings
from app.core.runtime import BOOT_ID
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)

JobTable = Literal["scrape_jobs", "media_jobs"]


def _active_statuses(table: JobTable) -> str:
    if table == "scrape_jobs":
        return "'queued', 'running'"
    return "'pending', 'running', 'processing', 'in_progress'"


async def claim(
    table: JobTable,
    job_id: str,
    *,
    work_item_id: str | None = None,
    lease_owner: str | None = None,
    lease_generation: int | None = None,
) -> None:
    """Record that this process owns the job, and start its heartbeat clock."""
    try:
        async with async_session_maker() as db:
            params = {
                "boot": BOOT_ID,
                "now": datetime.datetime.now(datetime.timezone.utc),
                "id": job_id,
            }
            guard = ""
            if work_item_id is not None:
                params.update(
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                )
                guard = (
                    " AND EXISTS (SELECT 1 FROM work_items wi WHERE wi.id = :work_item_id "
                    f"AND wi.job_id = {table}.id AND wi.status = 'running' "
                    "AND wi.lease_owner = :lease_owner AND wi.attempt_count = :lease_generation "
                    "AND wi.lease_until > :now)"
                )
            await db.execute(
                text(
                    f"UPDATE {table} SET owner_boot_id = :boot, heartbeat_at = :now "
                    f"WHERE id = :id AND status IN ({_active_statuses(table)}){guard}"
                ),
                params,
            )
            await db.commit()
    except Exception as e:
        # A missing heartbeat column must never stop a job from running; the
        # sweep falls back to created_at when heartbeat_at is null.
        logger.warning("Could not claim %s %s: %s", table, job_id, e)


async def _beat(
    table: JobTable,
    job_id: str,
    work_item_id: str | None,
    lease_owner: str | None,
    lease_generation: int | None,
) -> None:
    while True:
        await asyncio.sleep(settings.JOB_HEARTBEAT_INTERVAL_S)
        try:
            async with async_session_maker() as db:
                now = datetime.datetime.now(datetime.timezone.utc)
                params = {"now": now, "id": job_id, "boot": BOOT_ID}
                guard = ""
                if work_item_id is not None:
                    params.update(
                        work_item_id=work_item_id,
                        lease_owner=lease_owner,
                        lease_generation=lease_generation,
                    )
                    guard = (
                        " AND EXISTS (SELECT 1 FROM work_items wi WHERE wi.id = :work_item_id "
                        f"AND wi.job_id = {table}.id AND wi.status = 'running' "
                        "AND wi.lease_owner = :lease_owner AND wi.attempt_count = :lease_generation "
                        "AND wi.lease_until > :now)"
                    )
                await db.execute(
                    text(
                        f"UPDATE {table} SET heartbeat_at = :now WHERE id = :id "
                        f"AND owner_boot_id = :boot AND status IN ({_active_statuses(table)}){guard}"
                    ),
                    params,
                )
                await db.commit()
        except Exception as e:
            logger.warning("Heartbeat failed for %s %s: %s", table, job_id, e)


@contextlib.asynccontextmanager
async def heartbeat(
    table: JobTable,
    job_id: str,
    *,
    work_item_id: str | None = None,
    lease_owner: str | None = None,
    lease_generation: int | None = None,
):
    """Claim a job and keep it beating for the duration of the block."""
    await claim(
        table,
        job_id,
        work_item_id=work_item_id,
        lease_owner=lease_owner,
        lease_generation=lease_generation,
    )
    task = asyncio.create_task(
        _beat(table, job_id, work_item_id, lease_owner, lease_generation)
    )
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
