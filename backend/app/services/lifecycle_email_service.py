"""Customer lifecycle emails (welcome, trial-expiry) on top of email_service.

These are the conversion levers for a 7-day free trial: a user who gets a
welcome nudge activates more often, and a user warned before the trial lapses
converts instead of silently churning. Everything here is best-effort — email
is never a hard failure (see email_service), and every send is guarded by
``email_enabled()``.

Scheduling: there is no separate worker, so trial-expiry is sent from the
existing authenticated cron tick (``POST /api/monitors/tick``) via
``send_due_trial_reminders``. Welcome is sent inline at sign-up.
"""

from __future__ import annotations

import logging
import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.services.email_service import send_email, email_enabled

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return (settings.APP_BASE_URL or "http://localhost:5173").rstrip("/")


def _wrap(title: str, body_html: str, cta_label: str, cta_path: str) -> str:
    """Minimal branded HTML shell. Inline styles only (email clients strip <style>)."""
    url = f"{_base_url()}{cta_path}"
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#0A0A0A;color:#EDEDED;padding:32px;">
      <div style="max-width:560px;margin:0 auto;background:#111;border:1px solid #222;border-radius:12px;padding:32px;">
        <div style="font-size:13px;letter-spacing:2px;color:#6366F1;font-weight:700;margin-bottom:16px;">HELIX INTELLIGENCE</div>
        <h1 style="font-size:22px;margin:0 0 16px;color:#fff;">{title}</h1>
        <div style="font-size:15px;line-height:1.6;color:#B5B5B5;">{body_html}</div>
        <a href="{url}" style="display:inline-block;margin-top:24px;background:#6366F1;color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;">{cta_label}</a>
        <p style="margin-top:28px;font-size:12px;color:#666;">You received this because you created a Helix Intelligence account.</p>
      </div>
    </div>
    """


async def send_welcome_email(email_or_user: User | str, name: str = "") -> None:
    if not email_enabled():
        return
    if isinstance(email_or_user, str):
        target_email = email_or_user.strip()
        clean_name = (name or target_email.split("@")[0]).strip() or "there"
    else:
        target_email = getattr(email_or_user, "email", "")
        clean_name = (getattr(email_or_user, "full_name", None) or target_email.split("@")[0]).strip() or "there"

    if not target_email:
        return

    html = _wrap(
        f"Welcome to Helix, {clean_name}",
        "Your workspace is live with <strong>25 free credits</strong> and a 7-day trial. "
        "Run your first competitor discovery to see the ads winning in your market right now.",
        "Run your first discovery",
        "/discover",
    )
    result = await send_email(to=target_email, subject="Welcome to Helix Intelligence — your trial is live", html=html)
    logger.info("Welcome email to %s: %s", target_email, "sent" if result else getattr(result, "error", "failed"))



def _days_remaining(user: User) -> int | None:
    if not user.trial_expires_at:
        return None
    exp = user.trial_expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    return (exp - now).days


async def send_due_trial_reminders(db: AsyncSession) -> int:
    """Email users whose trial expires in ~2 days or ~0 days. Returns count sent.

    Idempotent within a day via the per-user ``admin_permissions`` JSON marker
    (``trial_reminder_sent_for``), avoiding a new column. Safe to call on every
    cron tick.
    """
    if not email_enabled():
        return 0

    result = await db.execute(
        select(User).where(User.trial_expires_at.isnot(None), User.role == "customer")
    )
    users = result.scalars().all()
    sent = 0
    today = datetime.date.today().isoformat()

    for user in users:
        days = _days_remaining(user)
        if days not in (0, 1, 2):
            continue
        perms = dict(user.admin_permissions or {})
        if perms.get("trial_reminder_sent_for") == today:
            continue

        label = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        html = _wrap(
            f"Your Helix trial ends {label}",
            "Your free trial and remaining credits expire soon. Upgrade to keep running "
            "discoveries, monitors, and creative generation without interruption.",
            "Keep my access",
            "/billing",
        )
        result_send = await send_email(
            to=user.email,
            subject=f"Your Helix trial ends {label}",
            html=html,
        )
        if result_send:
            perms["trial_reminder_sent_for"] = today
            user.admin_permissions = perms
            sent += 1

    if sent:
        await db.commit()
    logger.info("Trial reminders sent: %d", sent)
    return sent
