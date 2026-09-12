"""Scheduled competitor watches built on the existing Discover pipeline.

There is no queue and no worker process. A monitor run is the same
``run_discovery_pipeline`` call the Discover page makes, started from a cron
tick as an ``asyncio`` task on the web instance, and followed by a diff against
what the monitor saw last time.

Two things this deliberately does not reuse:

``trigger_search``
    It answers from a 12-hour dedup cache, which would make any cadence shorter
    than 12 hours silently return the previous job and report no changes.

A failed run is billed the same way as a failed Discover search: the credit
stays charged. The owner is told via an in-app notification, and via email
once Resend is configured, so an unattended failure is visible without a
separate refund rule.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import asyncio
import datetime
import logging
import traceback

from fastapi import HTTPException
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.monitor import Monitor, MonitorCreative, MonitorEvent, MonitorRun
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services.billing_service import (
    DISCOVER_SEARCH_CREDIT_COST,
    ESTIMATED_PROVIDER_COSTS,
    assert_can_spend,
    charge,
)
from app.services.creative_fingerprint import (
    CreativeSignature,
    PriorState,
    diff_run,
    signatures_for_run,
)
from app.services.email_service import SendResult, email_enabled, send_email
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

CADENCE_INTERVALS: Dict[str, datetime.timedelta] = {
    "every_6h": datetime.timedelta(hours=6),
    "every_12h": datetime.timedelta(hours=12),
    "daily": datetime.timedelta(days=1),
    "weekly": datetime.timedelta(days=7),
}

EVENT_LABELS = {
    "new_ad": "New ad",
    "killed_ad": "Ad stopped",
    "copy_changed": "Copy changed",
}


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _interval(cadence: str) -> datetime.timedelta:
    return CADENCE_INTERVALS.get(cadence, CADENCE_INTERVALS["daily"])


def _as_aware(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value


def _iso(value: Optional[datetime.datetime]) -> Optional[str]:
    aware = _as_aware(value)
    return aware.isoformat() if aware else None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize_monitor(monitor: Monitor, last_run: Optional[MonitorRun] = None) -> Dict[str, Any]:
    return {
        "id": monitor.id,
        "name": monitor.name,
        "query": monitor.query,
        "filters": monitor.filters or {},
        "cadence": monitor.cadence,
        "status": monitor.status,
        "paused_reason": monitor.paused_reason,
        "notify_in_app": bool(monitor.notify_in_app),
        "notify_email": bool(monitor.notify_email),
        "next_run_at": _iso(monitor.next_run_at),
        "last_run_at": _iso(monitor.last_run_at),
        "last_job_id": monitor.last_job_id,
        "baseline_at": _iso(monitor.baseline_at),
        "consecutive_failures": monitor.consecutive_failures or 0,
        "created_at": _iso(monitor.created_at),
        "last_run": serialize_run(last_run) if last_run else None,
    }


def serialize_run(run: MonitorRun) -> Dict[str, Any]:
    return {
        "id": run.id,
        "monitor_id": run.monitor_id,
        "job_id": run.job_id,
        "status": run.status,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "creatives_seen": run.creatives_seen,
        "new_count": run.new_count,
        "killed_count": run.killed_count,
        "changed_count": run.changed_count,
        "is_baseline": bool(run.is_baseline),
        "skipped_reason": run.skipped_reason,
        "error": run.error,
    }


def serialize_event(event: MonitorEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "monitor_id": event.monitor_id,
        "run_id": event.run_id,
        "type": event.type,
        "creative_id": event.creative_id,
        "headline": event.headline,
        "body": event.body,
        "cta": event.cta,
        "platform": event.platform,
        "landing_domain": event.landing_domain,
        "previous": event.previous,
        "created_at": _iso(event.created_at),
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def _load_owned(db: AsyncSession, monitor_id: str, org_id: str) -> Monitor:
    result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.org_id == org_id)
    )
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


async def create_monitor(
    db: AsyncSession,
    *,
    user: User,
    org_id: str,
    name: str,
    query: str,
    cadence: str = "daily",
    filters: Optional[Dict[str, Any]] = None,
    notify_in_app: bool = True,
    notify_email: bool = False,
) -> Dict[str, Any]:
    clean_query = (query or "").strip()
    if not clean_query:
        raise HTTPException(status_code=422, detail="A monitor needs a query to watch.")
    if cadence not in CADENCE_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown cadence '{cadence}'. Expected one of {sorted(CADENCE_INTERVALS)}.",
        )

    existing = await db.scalar(
        select(func.count(Monitor.id)).where(
            Monitor.org_id == org_id, Monitor.query == clean_query, Monitor.status == "active"
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"An active monitor for '{clean_query}' already exists.",
        )

    now = _utcnow()
    monitor = Monitor(
        org_id=org_id,
        user_id=user.id,
        name=(name or "").strip() or clean_query,
        query=clean_query,
        filters=filters or {},
        cadence=cadence,
        status="active",
        notify_in_app=notify_in_app,
        notify_email=notify_email,
        # Due immediately, so the first tick establishes the baseline instead of
        # the user waiting a full cadence to see anything happen.
        next_run_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    return serialize_monitor(monitor)


async def list_monitors(db: AsyncSession, org_id: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Monitor).where(Monitor.org_id == org_id).order_by(Monitor.created_at.desc())
    )
    monitors = list(result.scalars().all())
    if not monitors:
        return []

    ids = [m.id for m in monitors]
    runs_result = await db.execute(
        select(MonitorRun)
        .where(MonitorRun.monitor_id.in_(ids))
        .order_by(MonitorRun.started_at.desc())
    )
    latest: Dict[str, MonitorRun] = {}
    for run in runs_result.scalars().all():
        latest.setdefault(run.monitor_id, run)

    return [serialize_monitor(m, latest.get(m.id)) for m in monitors]


async def update_monitor(
    db: AsyncSession, monitor_id: str, org_id: str, changes: Dict[str, Any]
) -> Dict[str, Any]:
    monitor = await _load_owned(db, monitor_id, org_id)

    if "cadence" in changes and changes["cadence"] is not None:
        if changes["cadence"] not in CADENCE_INTERVALS:
            raise HTTPException(status_code=422, detail="Unknown cadence.")
        monitor.cadence = changes["cadence"]
        base = _as_aware(monitor.last_run_at) or _utcnow()
        monitor.next_run_at = base + _interval(monitor.cadence)

    for field in ("name", "notify_in_app", "notify_email"):
        if changes.get(field) is not None:
            setattr(monitor, field, changes[field])

    if changes.get("status") in ("active", "paused"):
        monitor.status = changes["status"]
        if monitor.status == "active":
            monitor.paused_reason = None
            monitor.consecutive_failures = 0
            if not monitor.next_run_at:
                monitor.next_run_at = _utcnow()

    monitor.updated_at = _utcnow()
    await db.commit()
    await db.refresh(monitor)
    return serialize_monitor(monitor)


async def delete_monitor(db: AsyncSession, monitor_id: str, org_id: str) -> Dict[str, Any]:
    monitor = await _load_owned(db, monitor_id, org_id)
    # Child rows carry no value once the monitor is gone and would otherwise
    # violate the foreign keys.
    for model in (MonitorEvent, MonitorCreative, MonitorRun):
        await db.execute(text(f"DELETE FROM {model.__tablename__} WHERE monitor_id = :id"), {"id": monitor.id})
    await db.delete(monitor)
    await db.commit()
    return {"success": True}


async def get_monitor_events(
    db: AsyncSession, org_id: str, monitor_id: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    query = (
        select(MonitorEvent)
        .join(Monitor, Monitor.id == MonitorEvent.monitor_id)
        .where(Monitor.org_id == org_id)
        .order_by(MonitorEvent.created_at.desc())
        .limit(min(limit, 200))
    )
    if monitor_id:
        query = query.where(MonitorEvent.monitor_id == monitor_id)
    result = await db.execute(query)
    return [serialize_event(e) for e in result.scalars().all()]


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

async def claim_due_monitors(db: AsyncSession, limit: int) -> List[str]:
    """Atomically take ownership of monitors that are due.

    ``next_run_at`` is pushed forward in the same statement that selects the
    rows, so two overlapping ticks cannot both pick up the same monitor and
    charge for it twice.
    """
    result = await db.execute(
        text(
            """
            UPDATE monitors SET
                next_run_at = now() + make_interval(secs => interval_s),
                last_run_at = now()
            FROM (
                SELECT id, CASE cadence
                    WHEN 'every_6h' THEN 21600
                    WHEN 'every_12h' THEN 43200
                    WHEN 'weekly' THEN 604800
                    ELSE 86400
                END AS interval_s
                FROM monitors
                WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= now()
                ORDER BY next_run_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            ) AS due
            WHERE monitors.id = due.id
            RETURNING monitors.id
            """
        ),
        {"limit": limit},
    )
    ids = [row[0] for row in result.fetchall()]
    await db.commit()
    return ids


async def tick(max_monitors: Optional[int] = None) -> Dict[str, Any]:
    """Dispatch due monitors and return immediately.

    A discovery run takes minutes, which is far longer than any cron provider
    will hold an HTTP request open, so runs are started as background tasks on
    the same instance and the tick reports only what it started. Crash safety
    comes from the existing job heartbeat and reconciliation sweep.
    """
    limit = max_monitors or settings.MONITOR_MAX_PER_TICK
    async with async_session_maker() as db:
        monitor_ids = await claim_due_monitors(db, limit)

    for monitor_id in monitor_ids:
        asyncio.create_task(run_monitor(monitor_id))

    return {"dispatched": len(monitor_ids), "monitor_ids": monitor_ids}


async def run_now(db: AsyncSession, monitor_id: str, org_id: str) -> Dict[str, Any]:
    monitor = await _load_owned(db, monitor_id, org_id)
    running = await db.scalar(
        select(func.count(MonitorRun.id)).where(
            MonitorRun.monitor_id == monitor.id, MonitorRun.status == "running"
        )
    )
    if running:
        raise HTTPException(status_code=409, detail="This monitor is already running.")

    monitor.last_run_at = _utcnow()
    monitor.next_run_at = _utcnow() + _interval(monitor.cadence)
    await db.commit()

    asyncio.create_task(run_monitor(monitor.id))
    return {"success": True, "monitor_id": monitor.id}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def _finish_run(
    run_id: str,
    *,
    status: str,
    creatives_seen: int = 0,
    new_count: int = 0,
    killed_count: int = 0,
    changed_count: int = 0,
    is_baseline: bool = False,
    skipped_reason: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    async with async_session_maker() as db:
        run = (await db.execute(select(MonitorRun).where(MonitorRun.id == run_id))).scalar_one_or_none()
        if not run:
            return
        run.status = status
        run.finished_at = _utcnow()
        run.creatives_seen = creatives_seen
        run.new_count = new_count
        run.killed_count = killed_count
        run.changed_count = changed_count
        run.is_baseline = is_baseline
        run.skipped_reason = skipped_reason
        run.error = error
        await db.commit()


async def run_monitor(monitor_id: str) -> None:
    """Execute one monitor end to end. Never raises: this runs detached."""
    try:
        await _run_monitor(monitor_id)
    except Exception as exc:
        logger.error("Monitor %s crashed: %s\n%s", monitor_id, exc, traceback.format_exc())


async def _run_monitor(monitor_id: str) -> None:
    from app.services.discover_service import run_discovery_pipeline

    async with async_session_maker() as db:
        monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
        if not monitor:
            return
        user = (await db.execute(select(User).where(User.id == monitor.user_id))).scalar_one_or_none()
        if not user:
            monitor.status = "paused"
            monitor.paused_reason = "The user who created this monitor no longer exists."
            await db.commit()
            return

        query = monitor.query
        filters = dict(monitor.filters or {})
        org_id = monitor.org_id
        is_baseline = monitor.baseline_at is None

        run = MonitorRun(monitor_id=monitor.id, status="running", started_at=_utcnow(), is_baseline=is_baseline)
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

        # Credits, trial state and the 'monitors' feature flag are all enforced
        # by the same gatekeeper the interactive Discover page uses, against the
        # monitor owner's plan.
        try:
            org, _plan = await assert_can_spend(
                db,
                user=user,
                required_credits=DISCOVER_SEARCH_CREDIT_COST,
                feature_name="monitors",
                lock_row=True,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            reason = detail.get("code", "blocked")
            message = detail.get("message", "This monitor could not run.")
            await _finish_run(run_id, status="skipped", skipped_reason=reason, error=message)
            await _handle_blocked(monitor_id, reason, message)
            return

        job = ScrapeJob(
            org_id=org_id,
            query=query,
            status="running",
            created_at=_utcnow(),
            progress=0.1,
            stage="init",
            stage_label="Monitor run",
            stage_index=0,
            stages_total=5,
            elapsed_ms=0,
            record_count=0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

        await charge(
            db=db,
            org=org,
            user_id=user.id,
            amount=DISCOVER_SEARCH_CREDIT_COST,
            provider="discover_composite",
            operation="monitor_run",
            units=1.0,
            cost_usd=ESTIMATED_PROVIDER_COSTS.get("apify_ad", 0.00075) * 15,
            job_id=job_id,
            metadata={"query": query, "monitor_id": monitor_id},
        )

        run.job_id = job_id
        monitor.last_job_id = job_id
        await db.commit()

    await run_discovery_pipeline(job_id, query, filters)

    async with async_session_maker() as db:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
        job_status = job.status if job else "failed"
        job_error = (job.error_msg if job else None) or "The discovery run did not complete."

    if job_status != "succeeded":
        # Same billing as a manual Discover search: the credit stays charged.
        # The owner is told, rather than refunded, so they can see the failure
        # without a different money rule.
        await _finish_run(run_id, status="failed", error=job_error)
        await _record_failure(monitor_id, job_error)
        await _notify_run_failed(monitor_id, job_error)
        return

    await _apply_diff(monitor_id, run_id, job_id, is_baseline)


async def _load_prior_states(db: AsyncSession, monitor_id: str) -> Dict[str, MonitorCreative]:
    result = await db.execute(select(MonitorCreative).where(MonitorCreative.monitor_id == monitor_id))
    return {row.identity_hash: row for row in result.scalars().all()}


async def _apply_diff(monitor_id: str, run_id: str, job_id: str, is_baseline: bool) -> None:
    async with async_session_maker() as db:
        creatives = list(
            (await db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()
        )
        signatures = signatures_for_run(creatives)
        stored = await _load_prior_states(db, monitor_id)
        previous = {
            identity: PriorState(identity, row.content_hash, row.status, row.missed_runs or 0)
            for identity, row in stored.items()
        }

        result = diff_run(
            signatures,
            previous,
            is_baseline=is_baseline,
            miss_threshold=settings.MONITOR_MISS_THRESHOLD,
        )

        now = _utcnow()

        # Snapshot the old copy before the rows below are overwritten with this
        # run's values, otherwise a copy_changed event would show the new text
        # as both the before and the after.
        prior_copy = {
            identity: {"headline": row.headline, "body": row.body, "cta": row.cta}
            for identity, row in stored.items()
        }

        # Remember everything seen this run, whether or not it produced an event.
        for sig in signatures:
            row = stored.get(sig.identity)
            if row is None:
                row = MonitorCreative(
                    monitor_id=monitor_id,
                    identity_hash=sig.identity,
                    content_hash=sig.content,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(row)
                stored[sig.identity] = row
            row.content_hash = sig.content
            row.status = "active"
            row.missed_runs = 0
            row.last_seen_at = now
            row.creative_id = sig.creative_id
            row.platform = sig.platform
            row.format = sig.format
            row.headline = sig.headline[:2000] if sig.headline else None
            row.body = sig.body[:4000] if sig.body else None
            row.cta = sig.cta[:500] if sig.cta else None
            row.landing_domain = sig.landing_domain

        for prior in result.pending_misses:
            row = stored.get(prior.identity)
            if row:
                row.missed_runs = (row.missed_runs or 0) + 1

        for prior in result.killed:
            row = stored.get(prior.identity)
            if row:
                row.missed_runs = (row.missed_runs or 0) + 1
                row.status = "gone"

        events: List[MonitorEvent] = []

        def add_event(event_type: str, sig: Optional[CreativeSignature], row: Optional[MonitorCreative], previous_copy=None):
            source = sig or row
            events.append(
                MonitorEvent(
                    monitor_id=monitor_id,
                    run_id=run_id,
                    type=event_type,
                    identity_hash=sig.identity if sig else row.identity_hash,
                    creative_id=getattr(source, "creative_id", None),
                    headline=(source.headline or None) if source else None,
                    body=(source.body or None) if source else None,
                    cta=(source.cta or None) if source else None,
                    platform=(source.platform or None) if source else None,
                    landing_domain=(source.landing_domain or None) if source else None,
                    previous=previous_copy,
                    created_at=now,
                )
            )

        for sig in result.new:
            add_event("new_ad", sig, None)

        for sig, _prior in result.changed:
            add_event("copy_changed", sig, None, previous_copy=prior_copy.get(sig.identity))

        for prior in result.killed:
            row = stored.get(prior.identity)
            if row:
                add_event("killed_ad", None, row)

        for event in events:
            db.add(event)

        monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
        if monitor:
            monitor.consecutive_failures = 0
            if is_baseline:
                monitor.baseline_at = now
        await db.commit()

    await _finish_run(
        run_id,
        status="succeeded",
        creatives_seen=len(signatures),
        new_count=len(result.new),
        killed_count=len(result.killed),
        changed_count=len(result.changed),
        is_baseline=is_baseline,
        skipped_reason=result.skipped_reason,
    )

    if result.total_events:
        await _fan_out(monitor_id, run_id, result)


# ---------------------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------------------

def _summary_line(result) -> str:
    parts = []
    if result.new:
        parts.append(f"{len(result.new)} new ad{'s' if len(result.new) != 1 else ''}")
    if result.changed:
        parts.append(f"{len(result.changed)} copy change{'s' if len(result.changed) != 1 else ''}")
    if result.killed:
        parts.append(f"{len(result.killed)} stopped")
    return ", ".join(parts)


def _render_email(monitor_name: str, query: str, result, link: str) -> str:
    def block(title: str, rows: Sequence[str]) -> str:
        if not rows:
            return ""
        items = "".join(f"<li style='margin:6px 0'>{r}</li>" for r in rows)
        return f"<h3 style='font:600 14px sans-serif;margin:20px 0 6px'>{title}</h3><ul style='padding-left:18px;font:14px sans-serif;color:#333'>{items}</ul>"

    def esc(v: Optional[str]) -> str:
        return (v or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:200]

    new_rows = [f"<strong>{esc(s.headline)}</strong><br><span style='color:#666'>{esc(s.cta)} · {esc(s.landing_domain)}</span>" for s in result.new[:10]]
    changed_rows = [f"<strong>{esc(s.headline)}</strong><br><span style='color:#666'>copy was edited</span>" for s, _ in result.changed[:10]]
    killed_rows = [f"<strong>{esc(getattr(p, 'headline', None))}</strong>" for p in result.killed[:10]]

    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif">
      <p style="color:#666;font-size:13px">Helix Intelligence · Monitor</p>
      <h2 style="margin:4px 0 2px">{esc(monitor_name)}</h2>
      <p style="color:#666;font-size:13px;margin:0 0 16px">Watching "{esc(query)}" · {_summary_line(result)}</p>
      {block(f"New ads ({len(result.new)})", new_rows)}
      {block(f"Copy changed ({len(result.changed)})", changed_rows)}
      {block(f"Stopped running ({len(result.killed)})", killed_rows)}
      <p style="margin-top:24px"><a href="{link}" style="background:#111;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-size:14px">View in Helix</a></p>
    </div>
    """


async def _fan_out(monitor_id: str, run_id: str, result) -> Optional[SendResult]:
    """Deliver the run's findings. Never raises into the run."""
    try:
        async with async_session_maker() as db:
            monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
            if not monitor:
                return None
            user = (await db.execute(select(User).where(User.id == monitor.user_id))).scalar_one_or_none()
            summary = _summary_line(result)
            link = f"/monitors?id={monitor.id}"

            if monitor.notify_in_app and user:
                await create_notification(
                    db,
                    user_id=user.id,
                    org_id=monitor.org_id,
                    type="info",
                    title=f"{monitor.name}: {summary}",
                    message=f'Your monitor for "{monitor.query}" found {summary}.',
                    link=link,
                )

            should_email = bool(monitor.notify_email and user and user.email)
            monitor_name, query, email_to = monitor.name, monitor.query, (user.email if user else None)

        if should_email:
            if not email_enabled():
                logger.info("Monitor %s wanted email but Resend is not configured.", monitor_id)
                return SendResult(False, error="not_configured")
            return await send_email(
                to=email_to,
                subject=f"{monitor_name}: {summary}",
                html=_render_email(monitor_name, query, result, f"{settings.APP_BASE_URL}{link}"),
                text=f'Your Helix monitor for "{query}" found {summary}. {settings.APP_BASE_URL}{link}',
            )
        return None
    except Exception as exc:
        logger.error("Monitor %s fan-out failed: %s", monitor_id, exc)
        return None


def _render_failure_email(monitor_name: str, query: str, message: str, link: str) -> str:
    def esc(v: Optional[str]) -> str:
        return (v or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:400]

    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif">
      <p style="color:#666;font-size:13px">Helix Intelligence · Monitor</p>
      <h2 style="margin:4px 0 2px">{esc(monitor_name)} failed</h2>
      <p style="color:#666;font-size:13px;margin:0 0 16px">Watching "{esc(query)}"</p>
      <p style="font:14px sans-serif;color:#333">{esc(message)}</p>
      <p style="font:13px sans-serif;color:#666">This run was charged the same as a Discover search. The credits were not refunded.</p>
      <p style="margin-top:24px"><a href="{link}" style="background:#111;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-size:14px">Open the monitor</a></p>
    </div>
    """


async def _notify_owner(monitor_id: str, title: str, message: str) -> None:
    """In-app always; email whenever Resend is configured and the owner has an address."""
    try:
        async with async_session_maker() as db:
            monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
            if not monitor:
                return
            user = (await db.execute(select(User).where(User.id == monitor.user_id))).scalar_one_or_none()
            if not user:
                return
            link = f"/monitors?id={monitor.id}"
            await create_notification(
                db,
                user_id=user.id,
                org_id=monitor.org_id,
                type="alert",
                title=title,
                message=message,
                link=link,
            )
            email_to = user.email
            monitor_name, query = monitor.name, monitor.query

        if email_to and email_enabled():
            await send_email(
                to=email_to,
                subject=title,
                html=_render_failure_email(monitor_name, query, message, f"{settings.APP_BASE_URL}{link}"),
                text=f"{title}. {message} {settings.APP_BASE_URL}{link}",
            )
    except Exception as exc:
        logger.error("Could not notify owner of monitor %s: %s", monitor_id, exc)


async def _notify_run_failed(monitor_id: str, error: str) -> None:
    short = (error or "The discovery run did not complete.").split("\n", 1)[0][:300]
    await _notify_owner(
        monitor_id,
        "Monitor run failed",
        (
            f"The scheduled search did not finish: {short} "
            "You were charged the same as a Discover search. Open the monitor to retry or pause it."
        ),
    )


async def notify_run_interrupted(monitor_id: str) -> None:
    """Used by the reconciler when a run dies with the process. No refund claim."""
    await _notify_owner(
        monitor_id,
        "Monitor run interrupted",
        (
            "A scheduled search was interrupted by a service restart. "
            "The next cadence will run it again. Open the monitor to check its status."
        ),
    )


async def _handle_blocked(monitor_id: str, reason: str, message: str) -> None:
    """A monitor that cannot pay stops rather than retrying forever."""
    async with async_session_maker() as db:
        monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
        if not monitor:
            return
        already_paused = monitor.status == "paused"
        if reason in ("trial_expired", "feature_disabled", "insufficient_credits"):
            monitor.status = "paused"
            monitor.paused_reason = message
        else:
            # A daily cap is temporary: try again on the next cadence rather
            # than pausing the monitor outright.
            monitor.paused_reason = message
        await db.commit()

    if not already_paused:
        await _notify_owner(monitor_id, "Monitor paused", message)


async def _record_failure(monitor_id: str, error: str) -> None:
    async with async_session_maker() as db:
        monitor = (await db.execute(select(Monitor).where(Monitor.id == monitor_id))).scalar_one_or_none()
        if not monitor:
            return
        monitor.consecutive_failures = (monitor.consecutive_failures or 0) + 1
        hit_limit = monitor.consecutive_failures >= settings.MONITOR_MAX_FAILURES
        if hit_limit:
            monitor.status = "paused"
            monitor.paused_reason = (
                f"Paused after {monitor.consecutive_failures} consecutive failed runs. "
                f"Last error: {error[:300]}"
            )
        reason = monitor.paused_reason
        await db.commit()

    if hit_limit:
        await _notify_owner(monitor_id, "Monitor paused after repeated failures", reason)
