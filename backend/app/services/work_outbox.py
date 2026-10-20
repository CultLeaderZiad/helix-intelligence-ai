"""Postgres outbox for long discovery, media, scout, maps, and monitor work.

A claim takes a short lease. The network call happens after the lease
transaction commits. Restarting a worker releases the lease; it does not
invent a completed result. A provider call that has already started is not
reported as aborted.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import classified_environment, settings
from app.core.tenancy import (
    apply_maintenance_context,
    apply_worker_claim_context,
    tenant_scope,
)
from app.db.session import async_session_maker, worker_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.work_item import WorkItem
from app.services.ai.call_policy import RetryableProviderError

logger = logging.getLogger(__name__)

QUEUED = "queued"
LEASED = "leased"
RUNNING = "running"
SUCCEEDED = "succeeded"
DEAD = "dead"
CANCELED = "canceled"


def inline_execution_enabled() -> bool:
    """Tests call the executor directly. Production never runs long work inline."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    if classified_environment() == "production":
        return False
    return bool(getattr(settings, "HELIX_DISPATCH_INLINE", False))


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _lease_seconds() -> int:
    return int(getattr(settings, "WORK_LEASE_S", 120) or 120)


def _max_attempts() -> int:
    return int(getattr(settings, "WORK_MAX_ATTEMPTS", 3) or 3)


async def enqueue_work(
    db,
    *,
    kind: str,
    job_id: str,
    org_id: str,
    user_id: Optional[str] = None,
    payload: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> Optional[WorkItem]:
    key = idempotency_key or f"{kind}:{job_id}"
    existing = (
        await db.execute(
            select(WorkItem).where(
                WorkItem.org_id == org_id,
                WorkItem.kind == kind,
                WorkItem.idempotency_key == key,
            )
        )
    ).scalars().first()
    if existing is not None:
        return existing
    item = WorkItem(
        org_id=org_id,
        user_id=user_id,
        kind=kind,
        job_id=job_id,
        payload=payload or {},
        status=QUEUED,
        attempt_count=0,
        max_attempts=_max_attempts(),
        idempotency_key=key,
        available_at=_now(),
    )
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return (
            await db.execute(
                select(WorkItem).where(
                    WorkItem.org_id == org_id,
                    WorkItem.kind == kind,
                    WorkItem.idempotency_key == key,
                )
            )
        ).scalars().first()
    return item


async def claim_next_work_item(owner: str) -> Optional[str]:
    """Lock one due row, then commit the lease before any provider call."""
    now = _now()
    async with worker_session_maker() as db:
        await apply_worker_claim_context(db, owner)
        item = (
            await db.execute(
                select(WorkItem)
                .where(
                    WorkItem.status == QUEUED,
                    WorkItem.available_at <= now,
                    WorkItem.cancel_requested.is_(None),
                )
                .order_by(WorkItem.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalars().first()
        if item is None:
            return None
        item.status = LEASED
        item.lease_owner = owner
        item.lease_until = now + datetime.timedelta(seconds=_lease_seconds())
        item.attempt_count = int(item.attempt_count or 0) + 1
        item.updated_at = now
        await db.commit()
        return item.id


async def mark_provider_started(item_id: str, operation_id: Optional[str] = None) -> None:
    async with async_session_maker() as db:
        item = await db.get(WorkItem, item_id)
        if item is None:
            return
        item.provider_started_at = _now()
        if operation_id:
            item.provider_operation_id = operation_id
        item.updated_at = _now()
        await db.commit()


async def request_cancel(job_id: str) -> str:
    """Signal active work and immediately cancel work that has not started."""
    async with async_session_maker() as db:
        items = (
            await db.execute(select(WorkItem).where(WorkItem.job_id == job_id))
        ).scalars().all()
        if not items:
            return "not_found"
        state = "canceled_before_provider"
        for item in items:
            if item.status in (SUCCEEDED, DEAD, CANCELED):
                continue
            item.cancel_requested = _now().isoformat()
            if item.status == QUEUED:
                item.status = CANCELED
            else:
                state = "cancellation_signaled"
            item.updated_at = _now()
        await db.commit()
        return state


async def requeue_expired_leases() -> int:
    """Return expired leases to the queue, or dead-letter them at the attempt cap."""
    now = _now()
    moved = 0
    async with async_session_maker() as db:
        await apply_maintenance_context(db, "work-lease-reaper")
        rows = (
            await db.execute(
                select(WorkItem).where(
                    WorkItem.status.in_((LEASED, RUNNING)),
                    WorkItem.lease_until.is_not(None),
                    WorkItem.lease_until < now,
                ).with_for_update(skip_locked=True)
            )
        ).scalars().all()
        for item in rows:
            item.lease_owner = None
            item.lease_until = None
            item.updated_at = now
            if item.cancel_requested:
                item.status = CANCELED
            elif int(item.attempt_count or 0) >= int(item.max_attempts or 1):
                item.status = DEAD
                item.last_error = item.last_error or "lease expired after the last attempt"
            else:
                item.status = QUEUED
                delay = min(60, 2 ** int(item.attempt_count or 1))
                item.available_at = now + datetime.timedelta(seconds=delay)
            moved += 1
        if moved:
            await db.commit()
        return moved


async def finish_work_item(
    item_id: str,
    *,
    status: str,
    error: Optional[str] = None,
    owner: Optional[str] = None,
    attempt_count: Optional[int] = None,
) -> bool:
    async with async_session_maker() as db:
        query = select(WorkItem).where(WorkItem.id == item_id)
        if owner is not None:
            query = query.where(
                WorkItem.status == RUNNING,
                WorkItem.lease_owner == owner,
                WorkItem.attempt_count == attempt_count,
                WorkItem.lease_until > _now(),
            )
        item = (await db.execute(query.with_for_update())).scalars().first()
        if item is None:
            return False
        item.status = status
        item.lease_owner = None
        item.lease_until = None
        item.last_error = (error or "")[:500] or None
        item.updated_at = _now()
        await db.commit()
        return True


async def defer_or_dead(
    item_id: str,
    error: str,
    *,
    owner: Optional[str] = None,
    attempt_count: Optional[int] = None,
) -> str:
    async with async_session_maker() as db:
        query = select(WorkItem).where(WorkItem.id == item_id)
        if owner is not None:
            query = query.where(
                WorkItem.status == RUNNING,
                WorkItem.lease_owner == owner,
                WorkItem.attempt_count == attempt_count,
                WorkItem.lease_until > _now(),
            )
        item = (await db.execute(query.with_for_update())).scalars().first()
        if item is None:
            return "stale"
        item.last_error = error[:500]
        item.lease_owner = None
        item.lease_until = None
        item.updated_at = _now()
        if int(item.attempt_count or 0) >= int(item.max_attempts or 1):
            item.status = DEAD
            await db.commit()
            return DEAD
        delay = min(60, 2 ** int(item.attempt_count or 1))
        item.status = QUEUED
        item.available_at = _now() + datetime.timedelta(seconds=delay)
        await db.commit()
        return QUEUED


async def retries_remaining(job_id: str) -> bool:
    async with async_session_maker() as db:
        item = (
            await db.execute(
                select(WorkItem)
                .where(WorkItem.job_id == job_id)
                .order_by(WorkItem.created_at.desc())
            )
        ).scalars().first()
        if item is None:
            return False
        return int(item.attempt_count or 0) < int(item.max_attempts or 1)


async def execute_work_item(item_id: str, owner: str) -> None:
    async with worker_session_maker() as db:
        await apply_worker_claim_context(db, owner)
        item = (
            await db.execute(
                select(WorkItem).where(
                    WorkItem.id == item_id,
                    WorkItem.status == LEASED,
                    WorkItem.lease_owner == owner,
                    WorkItem.lease_until > _now(),
                ).with_for_update()
            )
        ).scalars().first()
        if item is None:
            return
        if item.cancel_requested:
            item.status = CANCELED
            item.lease_owner = None
            item.lease_until = None
            await db.commit()
            return
        item.status = RUNNING
        item.lease_until = _now() + datetime.timedelta(seconds=_lease_seconds())
        item.updated_at = _now()
        kind = item.kind
        job_id = item.job_id
        payload = dict(item.payload or {})
        org_id = item.org_id
        user_id = item.user_id
        attempt_count = int(item.attempt_count or 0)
        await db.commit()

    async def dispatch() -> None:
        await _dispatch(
            kind,
            job_id,
            payload,
            org_id,
            user_id,
            item_id,
            owner,
            attempt_count,
        )

    async def watch_lease() -> Optional[str]:
        interval = max(0.1, min(float(settings.JOB_HEARTBEAT_INTERVAL_S), _lease_seconds() / 3))
        while True:
            await asyncio.sleep(interval)
            try:
                reason = await _renew_work_lease(item_id, owner, attempt_count, job_id, kind)
            except Exception as exc:
                logger.warning("Could not renew work lease %s: %s", item_id, exc)
                return "lease_lost"
            if reason:
                return reason

    # The global claim policy grants access to the queue row only. Work and
    # lease renewal run under the tenant bound to the claimed row.
    with tenant_scope([org_id], user_id or "", platform_admin=False, enforce=True):
        dispatch_task = asyncio.create_task(dispatch())
        lease_task = asyncio.create_task(watch_lease())
        try:
            done, _ = await asyncio.wait(
                (dispatch_task, lease_task), return_when=asyncio.FIRST_COMPLETED
            )
            if lease_task in done:
                reason = lease_task.result()
                if reason == "timed_out":
                    from app.services.discover_service import _finalize_discovery_job
                    await _finalize_discovery_job(
                        job_id,
                        status="timed_out",
                        failure_kind="deadline",
                        error="The search exceeded its server time limit. Please retry.",
                        work_item_id=item_id,
                        lease_owner=owner,
                        lease_generation=attempt_count,
                        refund_reason="deadline",
                    )
                elif reason == "cancelled":
                    from app.services.discover_service import _finalize_discovery_job
                    await _finalize_discovery_job(
                        job_id,
                        status="cancelled",
                        failure_kind="cancelled",
                        error="The search was cancelled.",
                        work_item_id=item_id,
                        lease_owner=owner,
                        lease_generation=attempt_count,
                        refund_reason="cancelled",
                    )
                dispatch_task.cancel()
                await asyncio.gather(dispatch_task, return_exceptions=True)
                if reason in ("timed_out", "cancelled"):
                    await finish_work_item(
                        item_id,
                        status=CANCELED,
                        owner=owner,
                        attempt_count=attempt_count,
                    )
                return
            await dispatch_task
        except asyncio.CancelledError:
            dispatch_task.cancel()
            await asyncio.gather(dispatch_task, return_exceptions=True)
            raise
        except RetryableProviderError as exc:
            await defer_or_dead(item_id, str(exc), owner=owner, attempt_count=attempt_count)
            return
        except Exception as exc:
            logger.exception("work item %s failed", item_id)
            await defer_or_dead(item_id, str(exc), owner=owner, attempt_count=attempt_count)
            return
        finally:
            lease_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await lease_task

        terminal_work_status = SUCCEEDED
        if kind == "discover":
            async with async_session_maker() as db:
                job = await db.get(ScrapeJob, job_id)
                if job is not None and job.status in ("cancelled", "timed_out"):
                    terminal_work_status = CANCELED
        await finish_work_item(
            item_id,
            status=terminal_work_status,
            owner=owner,
            attempt_count=attempt_count,
        )


async def _renew_work_lease(
    item_id: str,
    owner: str,
    attempt_count: int,
    job_id: str,
    kind: str,
) -> Optional[str]:
    now = _now()
    async with worker_session_maker() as db:
        await apply_worker_claim_context(db, owner)
        job = None
        if kind == "discover":
            job = (
                await db.execute(
                    select(ScrapeJob).where(ScrapeJob.id == job_id).with_for_update()
                )
            ).scalars().first()
        item = (
            await db.execute(
                select(WorkItem).where(
                    WorkItem.id == item_id,
                    WorkItem.status == RUNNING,
                    WorkItem.lease_owner == owner,
                    WorkItem.attempt_count == attempt_count,
                ).with_for_update()
            )
        ).scalars().first()
        if item is None or item.lease_until is None or item.lease_until <= now:
            return "lease_lost"
        if item.cancel_requested:
            return "cancelled"
        if kind == "discover":
            if job is None:
                return "lease_lost"
            if job.status == "cancelled":
                return "cancelled"
            if job.status == "timed_out":
                return "timed_out"
            if job.deadline_at is not None and job.deadline_at <= now:
                return "timed_out"
        item.lease_until = now + datetime.timedelta(seconds=_lease_seconds())
        item.updated_at = now
        await db.commit()
    return None


async def _dispatch(kind, job_id, payload, org_id, user_id, item_id, owner, attempt_count) -> None:
    if kind == "discover":
        from app.services.discover_service import run_discovery_pipeline
        await run_discovery_pipeline(
            job_id,
            payload.get("query") or "",
            payload.get("filters") or {},
            work_item_id=item_id,
            lease_owner=owner,
            lease_generation=attempt_count,
        )
        return
    if kind == "media":
        from app.services.media_service import gemini_generate_media_task
        custom_api_key = None
        token = payload.get("encrypted_byok")
        if token:
            from app.services.security_service import decrypt_secret
            custom_api_key = decrypt_secret(token)
        await gemini_generate_media_task(
            job_id,
            user_id,
            org_id,
            custom_api_key=custom_api_key,
            work_item_id=item_id,
        )
        return
    if kind == "scout":
        from app.services.scout_service import execute_scout_job
        await execute_scout_job(job_id)
        return
    if kind == "maps":
        from app.services.maps_scout_service import execute_maps_scout
        await execute_maps_scout(job_id)
        return
    if kind == "monitor":
        from app.services.monitor_service import run_monitor
        await run_monitor(job_id)
        return
    raise RuntimeError(f"unknown work kind {kind}")
