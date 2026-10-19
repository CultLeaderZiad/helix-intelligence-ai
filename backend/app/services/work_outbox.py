"""Postgres outbox for long discovery, media, scout, maps, and monitor work.

A claim takes a short lease. The network call happens after the lease
transaction commits. Restarting a worker releases the lease; it does not
invent a completed result. A provider call that has already started is not
reported as aborted.
"""

from __future__ import annotations

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
from app.models.work_item import WorkItem
from app.services.ai.call_policy import RetryableProviderError

logger = logging.getLogger(__name__)

QUEUED = "queued"
LEASED = "leased"
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
    """Cancel queued work. Work whose provider call already started is not aborted."""
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
            if item.provider_started_at is not None or item.status == LEASED:
                state = "provider_not_aborted"
            else:
                item.status = CANCELED
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
                    WorkItem.status == LEASED,
                    WorkItem.lease_until.is_not(None),
                    WorkItem.lease_until < now,
                )
            )
        ).scalars().all()
        for item in rows:
            item.lease_owner = None
            item.lease_until = None
            item.updated_at = now
            if int(item.attempt_count or 0) >= int(item.max_attempts or 1):
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


async def finish_work_item(item_id: str, *, status: str, error: Optional[str] = None) -> None:
    async with async_session_maker() as db:
        item = await db.get(WorkItem, item_id)
        if item is None:
            return
        item.status = status
        item.lease_owner = None
        item.lease_until = None
        item.last_error = (error or "")[:500] or None
        item.updated_at = _now()
        await db.commit()


async def defer_or_dead(item_id: str, error: str) -> str:
    async with async_session_maker() as db:
        item = await db.get(WorkItem, item_id)
        if item is None:
            return DEAD
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
                )
            )
        ).scalars().first()
        if item is None:
            return
        if item.cancel_requested and item.provider_started_at is None:
            item.status = CANCELED
            item.lease_owner = None
            item.lease_until = None
            await db.commit()
            return
        kind = item.kind
        job_id = item.job_id
        payload = dict(item.payload or {})
        org_id = item.org_id
        user_id = item.user_id

    # The global claim policy grants access to the queue row only. All work
    # execution and follow-up status writes run under the verified row org.
    with tenant_scope([org_id], user_id or "", platform_admin=False, enforce=True):
        try:
            await _dispatch(kind, job_id, payload, org_id, user_id, item_id)
        except RetryableProviderError as exc:
            await defer_or_dead(item_id, str(exc))
            return
        except Exception as exc:
            logger.exception("work item %s failed", item_id)
            await defer_or_dead(item_id, str(exc))
            return
        await finish_work_item(item_id, status=SUCCEEDED)


async def _dispatch(kind, job_id, payload, org_id, user_id, item_id) -> None:
    if kind == "discover":
        from app.services.discover_service import run_discovery_pipeline
        await run_discovery_pipeline(job_id, payload.get("query") or "", payload.get("filters") or {})
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
