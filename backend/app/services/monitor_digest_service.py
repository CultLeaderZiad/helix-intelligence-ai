"""Daily monitor digest: one summary of every monitor's changes per owner.

The per-run alert says what one monitor found. The digest rolls up all of a
user's monitors in one workspace since their last digest, at most once per
MONITOR_DIGEST_INTERVAL_H (default 24h):

* always as an in-app notification (type ``monitor_digest``), which is also
  the record of when the last digest went out;
* additionally by email when Resend is configured AND the user asked for
  email on at least one of those monitors.

It runs at the end of a monitor run, inside that run's tenant scope, so it
never reads across workspaces.
"""
from __future__ import annotations

import datetime
import logging
from collections import Counter, defaultdict
from typing import Optional

from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.monitor import Monitor, MonitorEvent
from app.models.notification import Notification
from app.models.user import User
from app.services.email_service import email_enabled, send_email
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

DIGEST_TYPE = "monitor_digest"
_LABELS = (("new_ad", "new"), ("copy_changed", "copy changed"), ("killed_ad", "stopped"))


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _aware(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def summarize(counts: Counter) -> str:
    parts = [f"{counts[key]} {label}" for key, label in _LABELS if counts.get(key)]
    return ", ".join(parts)


def _esc(value: Optional[str]) -> str:
    return (value or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:200]


def render_email(rows: list[tuple[str, str, str]], link: str) -> str:
    items = "".join(
        f"<li style='margin:6px 0'><strong>{_esc(name)}</strong> "
        f"<span style='color:#666'>(\"{_esc(query)}\")</span>: {_esc(summary)}</li>"
        for name, query, summary in rows
    )
    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif">
      <p style="color:#666;font-size:13px">Helix Intelligence · Daily monitor digest</p>
      <ul style="padding-left:18px;font:14px sans-serif;color:#333">{items}</ul>
      <p style="margin-top:24px"><a href="{link}" style="background:#111;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-size:14px">Open Monitors</a></p>
    </div>
    """


async def maybe_send_digest(org_id: str, user_id: str, *, now: Optional[datetime.datetime] = None) -> Optional[dict]:
    """Send the digest if one is due and there is something to report. Never raises."""
    now = now or _now()
    interval = datetime.timedelta(hours=int(settings.MONITOR_DIGEST_INTERVAL_H))
    try:
        async with async_session_maker() as db:
            last = (await db.execute(
                select(Notification.created_at)
                .where(Notification.user_id == user_id, Notification.org_id == org_id, Notification.type == DIGEST_TYPE)
                .order_by(Notification.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            last = _aware(last)
            if last is not None and now - last < interval:
                return None
            since = last or (now - interval)
            monitors = (await db.execute(
                select(Monitor).where(Monitor.org_id == org_id, Monitor.user_id == user_id)
            )).scalars().all()
            if not monitors:
                return None
            by_id = {m.id: m for m in monitors}
            events = (await db.execute(
                select(MonitorEvent.monitor_id, MonitorEvent.type)
                .where(MonitorEvent.monitor_id.in_(list(by_id)), MonitorEvent.created_at > since)
            )).all()
            counts: dict[str, Counter] = defaultdict(Counter)
            for monitor_id, event_type in events:
                counts[monitor_id][event_type] += 1
            rows = [
                (by_id[mid].name, by_id[mid].query, summarize(c))
                for mid, c in sorted(counts.items(), key=lambda kv: by_id[kv[0]].name.lower())
                if summarize(c)
            ]
            if not rows:
                return None
            total = Counter()
            for c in counts.values():
                total.update(c)
            headline = summarize(total)
            title = f"Monitor digest: {headline} across {len(rows)} monitor{'s' if len(rows) != 1 else ''}"
            message = "; ".join(f'{name} ("{query}"): {summary}' for name, query, summary in rows)[:1000]
            await create_notification(db, user_id=user_id, org_id=org_id, type=DIGEST_TYPE,
                                      title=title, message=message, link="/monitors")
            wants_email = any(m.notify_email for m in monitors if m.id in counts)
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            email_to = user.email if user else None
        emailed = False
        if wants_email and email_to and email_enabled():
            result = await send_email(
                to=email_to,
                subject=title,
                html=render_email(rows, f"{settings.APP_BASE_URL}/monitors"),
                text=f"{title}. {message} {settings.APP_BASE_URL}/monitors",
            )
            emailed = bool(getattr(result, "accepted", False))
        return {"monitors": len(rows), "summary": headline, "emailed": emailed}
    except Exception as exc:
        logger.error("Monitor digest for user %s failed: %s", user_id, exc)
        return None
