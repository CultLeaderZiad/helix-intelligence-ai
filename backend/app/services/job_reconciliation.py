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
from app.core.tenancy import (
    apply_maintenance_context,
    apply_monitor_maintenance_lookup_context,
    tenant_scope,
)
from app.db.session import async_session_maker
from app.services.billing_service import DISCOVER_SEARCH_CREDIT_COST, refund

logger = logging.getLogger(__name__)

DISCOVER_ACTIVE = ("queued", "running")
# 'in_progress' is set by a generation task while it waits for completion.
# It was missing from the original sweep, so a media job interrupted during
# that wait stayed active forever.
MEDIA_ACTIVE = ("pending", "running", "processing", "in_progress")
SCOUT_ACTIVE = ("queued", "running")
MAPS_ACTIVE = ("queued", "running")
LEADGEN_ACTIVE = ("queued", "running")

DISCOVER_MESSAGE = (
    "Interrupted by a service restart, not by a problem with your search. "
    "The credits for this run were refunded. Please run it again."
)
MEDIA_MESSAGE = (
    "Interrupted by a service restart, not by a problem with your prompt. "
    "You were not charged. Please try generating again."
)
SCOUT_MESSAGE = (
    "Interrupted by a service restart. Any credits deducted for this run were refunded. Please run it again."
)
MAPS_MESSAGE = (
    "Interrupted by a service restart. Any credits deducted for this run were refunded. Please run it again."
)
LEADGEN_MESSAGE = (
    "Interrupted by a worker or service restart. Any credits deducted for this run were refunded. Please run it again."
)


async def _sweep_table(
    table: str,
    statuses: tuple,
    error_column: str,
    message: str,
    select_extra: str = "",
    has_failure_kind: bool = True,
    extra_update_clauses: str = "",
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
        AND NOT EXISTS (
            SELECT 1 FROM work_items wi
            WHERE wi.job_id = {table}.id
              AND wi.status IN ('queued', 'leased')
              AND wi.attempt_count < wi.max_attempts
        )
    """
    params = {"boot": BOOT_ID, "cutoff": cutoff}

    async with async_session_maker() as db:
        await apply_maintenance_context(db, BOOT_ID)
        lock_suffix = " FOR UPDATE SKIP LOCKED" if db.bind and db.bind.dialect.name == "postgresql" else ""
        rows = (
            await db.execute(
                text(f"SELECT id{select_extra} FROM {table} WHERE {predicate}{lock_suffix}"), params
            )
        ).mappings().all()
        if not rows:
            return []

        ids = [r["id"] for r in rows]
        id_placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        id_params = {f"id_{i}": row_id for i, row_id in enumerate(ids)}
        
        failure_kind_clause = "failure_kind = 'service_restart'," if has_failure_kind else ""
        extra_clauses = f", {extra_update_clauses}" if extra_update_clauses else ""
        
        await db.execute(
            text(
                f"""UPDATE {table}
                    SET status = 'failed',
                        {failure_kind_clause}
                        {error_column} = :message
                        {extra_clauses}
                    WHERE id IN ({id_placeholders})"""
            ),
            {**id_params, "message": message},
        )
        await db.commit()

    return [dict(r) for r in rows]


async def _sweep_unrefunded_failed_jobs() -> List[Dict[str, Any]]:
    """Sweep scrape jobs that failed but have not had their credits refunded yet (F08)."""
    async with async_session_maker() as db:
        await apply_maintenance_context(db, BOOT_ID)
        lock_suffix = " FOR UPDATE OF sj SKIP LOCKED" if db.bind and db.bind.dialect.name == "postgresql" else ""
        query = text(f"""
            SELECT sj.id, sj.org_id
            FROM scrape_jobs sj
            JOIN usage_logs ul_charge ON ul_charge.job_id = sj.id AND ul_charge.credits_deducted > 0
            WHERE sj.status = 'failed'
              AND NOT EXISTS (
                  SELECT 1 FROM usage_logs ul_refund
                  WHERE ul_refund.job_id = sj.id AND ul_refund.credits_deducted < 0
              )
            {lock_suffix}
            LIMIT 50
        """)
        rows = (await db.execute(query)).mappings().all()
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
        await apply_maintenance_context(db, BOOT_ID)
        result = await db.execute(
            text(
                """
                UPDATE monitor_runs AS r
                SET status = 'failed',
                    finished_at = now(),
                    skipped_reason = 'service_restart',
                    error = 'Interrupted by a service restart. The next scheduled run will pick up where this left off.'
                FROM (
                    SELECT mr.id, mr.monitor_id
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
        monitor_targets = [row[0] for row in result.fetchall()]
        await db.commit()

    if monitor_targets:
        from app.services.monitor_service import notify_run_interrupted

        for monitor_id in dict.fromkeys(monitor_targets):
            try:
                async with async_session_maker() as db:
                    await apply_monitor_maintenance_lookup_context(db, monitor_id)
                    org_id = (
                        await db.execute(
                            text("SELECT org_id FROM monitors WHERE id = :monitor_id"),
                            {"monitor_id": monitor_id},
                        )
                    ).scalar_one_or_none()
                if not org_id:
                    continue
                with tenant_scope([org_id], "", platform_admin=False, enforce=True):
                    await notify_run_interrupted(monitor_id)
            except Exception as exc:
                logger.error("Could not notify owner of interrupted monitor %s: %s", monitor_id, exc)
    return len(monitor_targets)


async def reconcile_once() -> Dict[str, int]:
    """One reconciliation pass. Safe to call repeatedly."""
    swept = {"discover": 0, "media": 0, "refunded": 0, "monitor_runs": 0}
    try:
        from app.services.work_outbox import requeue_expired_leases
        swept["requeued"] = await requeue_expired_leases()
    except Exception as exc:
        logger.error("Work lease requeue failed: %s", exc)

    try:
        discover_rows = await _sweep_table(
            "scrape_jobs", DISCOVER_ACTIVE, "error_msg", DISCOVER_MESSAGE, ", org_id"
        )
        swept["discover"] = len(discover_rows)
    except Exception as e:
        logger.error("Discover reconciliation failed: %s", e)
        discover_rows = []

    # Discover charges upfront, so an interrupted run took money for a result
    # the user can never receive. Also refund any failed jobs that crashed before refund could run (F08).
    failed_unrefunded = []
    try:
        failed_unrefunded = await _sweep_unrefunded_failed_jobs()
    except Exception as e:
        logger.error("Sweep unrefunded failed jobs failed: %s", e)

    all_to_refund = {r["id"]: r for r in discover_rows}
    for r in failed_unrefunded:
        all_to_refund[r["id"]] = r

    for job_id, row in all_to_refund.items():
        try:
            with tenant_scope([row["org_id"]], "", platform_admin=False, enforce=True):
                async with async_session_maker() as db:
                    await refund(
                        db,
                        row["org_id"],
                        DISCOVER_SEARCH_CREDIT_COST,
                        "service_restart_sweep",
                        job_id,
                    )
            swept["refunded"] += 1
        except Exception as e:
            logger.error("Refund failed for swept job %s: %s", job_id, e)

    try:
        media_rows = await _sweep_table(
            "media_jobs", MEDIA_ACTIVE, "error_message", MEDIA_MESSAGE
        )
        swept["media"] = len(media_rows)
    except Exception as e:
        logger.error("Media reconciliation failed: %s", e)

    # 3. Social Scout Jobs (F25)
    try:
        scout_rows = await _sweep_table(
            "scout_jobs",
            SCOUT_ACTIVE,
            "error_msg",
            SCOUT_MESSAGE,
            select_extra=", org_id, credits_used",
            has_failure_kind=False,
            extra_update_clauses="stage = 'failed', stage_label = 'Failed'"
        )
        swept["scout"] = len(scout_rows)
        for r in scout_rows:
            credits = float(r.get("credits_used") or 0.0)
            if credits > 0:
                try:
                    with tenant_scope([r["org_id"]], "", platform_admin=False, enforce=True):
                        async with async_session_maker() as db:
                            await refund(db, r["org_id"], credits, "scout_service_restart_sweep", r["id"])
                    swept["refunded"] += 1
                except Exception as e:
                    logger.error("Refund failed for swept scout job %s: %s", r["id"], e)
    except Exception as e:
        logger.error("Scout reconciliation failed: %s", e)

    # 4. Maps Scout Jobs (F25)
    try:
        maps_rows = await _sweep_table(
            "scout_maps_jobs",
            MAPS_ACTIVE,
            "error_msg",
            MAPS_MESSAGE,
            select_extra=", org_id, credits_used",
            has_failure_kind=False,
            extra_update_clauses="stage = 'failed', stage_label = 'Failed'"
        )
        swept["maps"] = len(maps_rows)
        for r in maps_rows:
            credits = float(r.get("credits_used") or 0.0)
            if credits > 0:
                try:
                    with tenant_scope([r["org_id"]], "", platform_admin=False, enforce=True):
                        async with async_session_maker() as db:
                            await refund(db, r["org_id"], credits, "maps_service_restart_sweep", r["id"])
                    swept["refunded"] += 1
                except Exception as e:
                    logger.error("Refund failed for swept maps job %s: %s", r["id"], e)
    except Exception as e:
        logger.error("Maps reconciliation failed: %s", e)

    # 5. LeadGen Jobs (F25)
    try:
        leadgen_rows = await _sweep_table(
            "leadgen_jobs",
            LEADGEN_ACTIVE,
            "error_msg",
            LEADGEN_MESSAGE,
            select_extra=", org_id, credits_used",
            has_failure_kind=False,
            extra_update_clauses="stage = 'failed', stage_label = 'Failed'"
        )
        swept["leadgen"] = len(leadgen_rows)
        for r in leadgen_rows:
            credits = float(r.get("credits_used") or 0.0)
            if credits > 0:
                try:
                    with tenant_scope([r["org_id"]], "", platform_admin=False, enforce=True):
                        async with async_session_maker() as db:
                            await refund(db, r["org_id"], credits, "leadgen_service_restart_sweep", r["id"])
                    swept["refunded"] += 1
                except Exception as e:
                    logger.error("Refund failed for swept leadgen job %s: %s", r["id"], e)
    except Exception as e:
        logger.error("LeadGen reconciliation failed: %s", e)

    try:
        swept["monitor_runs"] = await _sweep_monitor_runs()
    except Exception as e:
        logger.error("Monitor run reconciliation failed: %s", e)

    if (
        swept["discover"]
        or swept["media"]
        or swept.get("scout")
        or swept.get("maps")
        or swept.get("leadgen")
        or swept["monitor_runs"]
    ):
        logger.warning(
            "Job reconciliation: %d discover, %d media, %d scout, %d maps, %d leadgen (%d total refunded), %d monitor runs marked failed.",
            swept["discover"],
            swept["media"],
            swept.get("scout", 0),
            swept.get("maps", 0),
            swept.get("leadgen", 0),
            swept["refunded"],
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
