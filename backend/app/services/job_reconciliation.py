"""Clean up jobs whose owning process died.

Background work runs as ``asyncio`` tasks inside the web process. A restart or
redeploy kills those tasks while the database row stays ``running`` forever, so
the client polls a job that nobody is working on.

A job is considered dead when both of these hold:

* it is owned by a different process lifetime than the current one (or by no
  recorded process at all, which is true of rows written before this change),
  and
* it has been silent for longer than ``JOB_STALE_AFTER_S`` -- no heartbeat, and
  for legacy rows no activity since creation.

Requiring silence rather than total age is what makes a short threshold safe.
Discovery runs in this app reach 5.3 minutes at p95, so an age-only rule has to
wait out the slowest legitimate job before it can call anything dead. A live
job heartbeats every 15 seconds, so two minutes of silence means dead no matter
how long the job was always going to take.

The sweep runs at startup and then on a timer, because a restart that completes
quickly happens before the killed job is old enough to look stale.
"""

import asyncio
import datetime
import logging
from typing import Any, Dict, List

from sqlalchemy import text

from app.core.config import settings
from app.core.runtime import BOOT_ID
from app.db.session import async_session_maker
from app.services.billing_service import DISCOVER_SEARCH_CREDIT_COST, refund

logger = logging.getLogger(__name__)

DISCOVER_ACTIVE = ("queued", "running")
# 'in_progress' is set by the Higgsfield path while it waits for the webhook.
# It was missing from the original sweep, so a media job interrupted during
# that wait stayed active forever.
MEDIA_ACTIVE = ("pending", "running", "processing", "in_progress")

DISCOVER_MESSAGE = (
    "Interrupted by a service restart, not by a problem with your search. "
    "The credits for this run were refunded. Please run it again."
)
MEDIA_MESSAGE = (
    "Interrupted by a service restart, not by a problem with your prompt. "
    "You were not charged. Please try generating again."
)


async def _sweep_table(
    table: str,
    statuses: tuple,
    error_column: str,
    message: str,
    select_extra: str = "",
) -> List[Dict[str, Any]]:
    """Mark dead rows failed, returning what was swept."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        seconds=settings.JOB_STALE_AFTER_S
    )
    placeholders = ", ".join(f"'{s}'" for s in statuses)
    predicate = f"""
        status IN ({placeholders})
        AND (owner_boot_id IS NULL OR owner_boot_id <> :boot)
        AND COALESCE(heartbeat_at, created_at) < :cutoff
    """
    params = {"boot": BOOT_ID, "cutoff": cutoff}

    async with async_session_maker() as db:
        rows = (
            await db.execute(
                text(f"SELECT id{select_extra} FROM {table} WHERE {predicate}"), params
            )
        ).mappings().all()
        if not rows:
            return []

        await db.execute(
            text(
                f"""UPDATE {table}
                    SET status = 'failed',
                        failure_kind = 'service_restart',
                        {error_column} = :message
                    WHERE {predicate}"""
            ),
            {**params, "message": message},
        )
        await db.commit()

    return [dict(r) for r in rows]


async def _sweep_monitor_runs() -> int:
    """Close out monitor runs whose work is no longer happening.

    A ``monitor_runs`` row has no heartbeat of its own; it is a wrapper around a
    scrape job that does. So a run is dead once its job has already reached a
    terminal state and nothing picked the result up, or once it has outlived any
    plausible discovery run. Left alone these rows stay 'running' forever and
    the monitor refuses to start again.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    stale_cutoff = now - datetime.timedelta(seconds=settings.JOB_STALE_AFTER_S)
    hard_cutoff = now - datetime.timedelta(seconds=settings.MONITOR_RUN_TIMEOUT_S)

    async with async_session_maker() as db:
        result = await db.execute(
            text(
                """
                UPDATE monitor_runs AS r
                SET status = 'failed',
                    finished_at = now(),
                    skipped_reason = 'service_restart',
                    error = 'Interrupted by a service restart. The next scheduled run will pick up where this left off.'
                FROM (
                    SELECT mr.id
                    FROM monitor_runs mr
                    LEFT JOIN scrape_jobs sj ON sj.id = mr.job_id
                    WHERE mr.status = 'running'
                      AND (
                            mr.started_at < :hard_cutoff
                        OR (mr.started_at < :stale_cutoff
                            AND (mr.job_id IS NULL OR sj.status IN ('failed', 'succeeded')))
                      )
                ) AS dead
                WHERE r.id = dead.id
                RETURNING r.monitor_id
                """
            ),
            {"stale_cutoff": stale_cutoff, "hard_cutoff": hard_cutoff},
        )
        monitor_ids = [row[0] for row in result.fetchall()]
        await db.commit()

    if monitor_ids:
        from app.services.monitor_service import notify_run_interrupted

        for monitor_id in dict.fromkeys(monitor_ids):
            try:
                await notify_run_interrupted(monitor_id)
            except Exception as exc:
                logger.error("Could not notify owner of interrupted monitor %s: %s", monitor_id, exc)
    return len(monitor_ids)


async def reconcile_once() -> Dict[str, int]:
    """One reconciliation pass. Safe to call repeatedly."""
    swept = {"discover": 0, "media": 0, "refunded": 0, "monitor_runs": 0}

    try:
        discover_rows = await _sweep_table(
            "scrape_jobs", DISCOVER_ACTIVE, "error_msg", DISCOVER_MESSAGE, ", org_id"
        )
        swept["discover"] = len(discover_rows)
    except Exception as e:
        logger.error("Discover reconciliation failed: %s", e)
        discover_rows = []

    # Discover charges upfront, so an interrupted run took money for a result
    # the user can never receive. Media only charges on success, so there is
    # nothing to give back there.
    for row in discover_rows:
        try:
            async with async_session_maker() as db:
                await refund(
                    db,
                    row["org_id"],
                    DISCOVER_SEARCH_CREDIT_COST,
                    "service_restart_sweep",
                    row["id"],
                )
            swept["refunded"] += 1
        except Exception as e:
            logger.error("Refund failed for swept job %s: %s", row["id"], e)

    try:
        media_rows = await _sweep_table(
            "media_jobs", MEDIA_ACTIVE, "error_message", MEDIA_MESSAGE
        )
        swept["media"] = len(media_rows)
    except Exception as e:
        logger.error("Media reconciliation failed: %s", e)

    try:
        swept["monitor_runs"] = await _sweep_monitor_runs()
    except Exception as e:
        logger.error("Monitor run reconciliation failed: %s", e)

    if swept["discover"] or swept["media"] or swept["monitor_runs"]:
        logger.warning(
            "Job reconciliation: %d discover (%d refunded), %d media, %d monitor runs marked failed.",
            swept["discover"],
            swept["refunded"],
            swept["media"],
            swept["monitor_runs"],
        )
    return swept


async def reconciliation_loop(interval_s: int = 60) -> None:
    """Sweep on a timer.

    A startup-only sweep misses the common case: the process dies, comes back
    within seconds, and the job it killed is not yet old enough to look stale.
    Nothing would ever look at it again. The timer closes that gap so the user
    finds out in about two minutes instead of never.
    """
    while True:
        try:
            await asyncio.sleep(interval_s)
            await reconcile_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Reconciliation loop error: %s", e)
