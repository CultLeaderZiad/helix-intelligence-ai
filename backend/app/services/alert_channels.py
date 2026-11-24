"""Alerts to Telegram chats and signed webhooks.

Every in-app notification for a workspace (notification_service) is fanned out
to the workspace's enabled channels as ``alert`` work items, so delivery runs
in the durable outbox: a failing channel never blocks a monitor run, and a
failed send is retried with backoff (work_outbox.defer_or_dead). After
ALERT_MAX_CONSECUTIVE_FAILURES failures in a row a channel is disabled and the
owner is told in-app.

Limits come from plans.limits (alert_telegram_chats, alert_webhooks,
alerts_per_day) with ALERT_DEFAULT_* fallbacks. The daily count is read from
work_items (kind='alert'), so it lives in the database, not in memory.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import logging
import secrets
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification_channel import NotificationChannel

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
LINK_CODE_TTL = datetime.timedelta(minutes=15)
TYPES = ("telegram", "webhook")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def telegram_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME)


async def alert_limits(db: AsyncSession, org_id: str) -> Dict[str, int]:
    from app.services.provider_budget import plan_limits

    limits = await plan_limits(db, org_id)

    def pick(key: str, default: int) -> int:
        value = limits.get(key)
        return int(default if value is None else value)

    return {
        "telegram": pick("alert_telegram_chats", settings.ALERT_DEFAULT_TELEGRAM_CHATS),
        "webhook": pick("alert_webhooks", settings.ALERT_DEFAULT_WEBHOOKS),
        "per_day": pick("alerts_per_day", settings.ALERT_DEFAULT_PER_DAY),
    }


def public_view(ch: NotificationChannel) -> Dict[str, Any]:
    """What the API returns: never the chat id, URL secret or link code."""
    iso = lambda d: d.isoformat() if d else None  # noqa: E731
    return {
        "id": ch.id, "type": ch.type, "status": ch.status, "label": ch.label, "enabled": bool(ch.enabled),
        "last_success_at": iso(ch.last_success_at), "last_failure_at": iso(ch.last_failure_at),
        "last_error": ch.last_error, "consecutive_failures": int(ch.consecutive_failures or 0),
        "created_at": iso(ch.created_at),
    }


async def list_channels(db: AsyncSession, org_id: str) -> List[NotificationChannel]:
    rows = await db.execute(
        select(NotificationChannel).where(NotificationChannel.org_id == org_id).order_by(NotificationChannel.created_at)
    )
    return list(rows.scalars().all())


async def _check_room(db: AsyncSession, org_id: str, kind: str) -> None:
    limits = await alert_limits(db, org_id)
    used = await db.scalar(
        select(func.count(NotificationChannel.id)).where(
            NotificationChannel.org_id == org_id, NotificationChannel.type == kind,
            NotificationChannel.status != "disabled",
        )
    )
    if int(used or 0) >= limits[kind]:
        raise HTTPException(status_code=403, detail={
            "code": "alert_channel_limit",
            "message": f"Your plan allows {limits[kind]} {kind} channel(s). Remove one first.",
        })


def _mask_url(url: str) -> str:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}/…"


async def create_webhook(db: AsyncSession, org_id: str, user_id: str, url: str) -> Dict[str, Any]:
    from app.services.safe_fetch import UnsafeFetch, assert_public_http_url
    from app.services.security_service import encrypt_secret

    url = (url or "").strip()
    if not url.lower().startswith("https://"):
        raise HTTPException(status_code=422, detail={"code": "webhook_https_required", "message": "Use an https:// URL."})
    try:
        assert_public_http_url(url)
    except UnsafeFetch as exc:
        raise HTTPException(status_code=422, detail={"code": "webhook_url_blocked", "message": str(exc)})
    await _check_room(db, org_id, "webhook")
    secret = "whsec_" + secrets.token_urlsafe(32)
    ch = NotificationChannel(
        org_id=org_id, created_by=user_id, type="webhook", status="active", label=_mask_url(url),
        config_encrypted=encrypt_secret(json.dumps({"url": url, "secret": secret})), enabled=True,
        consecutive_failures=0,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    # The signing secret is returned once and never again.
    return {"channel": public_view(ch), "signing_secret": secret}


async def start_telegram_link(db: AsyncSession, org_id: str, user_id: str) -> Dict[str, Any]:
    if not telegram_configured():
        raise HTTPException(status_code=503, detail={"code": "telegram_not_configured", "message": "Telegram alerts are not set up on this server."})
    await _check_room(db, org_id, "telegram")
    code = secrets.token_urlsafe(16).replace("-", "").replace("_", "")[:24]
    ch = NotificationChannel(
        org_id=org_id, created_by=user_id, type="telegram", status="pending", label="Telegram (waiting for /start)",
        link_code_hash=_hash(code), link_code_expires_at=_now() + LINK_CODE_TTL, enabled=True, consecutive_failures=0,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return {
        "channel": public_view(ch),
        "link": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={code}",
        "expires_at": ch.link_code_expires_at.isoformat(),
    }


async def complete_telegram_link(db: AsyncSession, code: str, chat_id: int, chat_title: str) -> bool:
    """Called from the verified Telegram webhook. Looks the code up across
    workspaces (platform scope, by hash only), then writes inside the owner's scope."""
    from app.core.tenancy import apply_tenant_context, tenant_scope
    from app.services.security_service import encrypt_secret

    with tenant_scope(None, "", platform_admin=True, enforce=True):
        await apply_tenant_context(db)
        ch = (await db.execute(
            select(NotificationChannel).where(NotificationChannel.link_code_hash == _hash(code))
        )).scalar_one_or_none()
        org_id = ch.org_id if ch is not None else None
        await db.rollback()
    if ch is None or org_id is None:
        return False
    with tenant_scope([org_id], "", platform_admin=False, enforce=True):
        await apply_tenant_context(db)
        ch = (await db.execute(
            select(NotificationChannel).where(NotificationChannel.link_code_hash == _hash(code))
        )).scalar_one_or_none()
        expires = ch.link_code_expires_at if ch is not None else None
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=datetime.timezone.utc)
        if ch is None or ch.status != "pending" or expires is None or expires < _now():
            await db.rollback()
            return False
        ch.config_encrypted = encrypt_secret(json.dumps({"chat_id": chat_id}))
        ch.label = f"Telegram: {chat_title[:60]}" if chat_title else "Telegram"
        ch.status = "active"
        ch.link_code_hash = None
        ch.link_code_expires_at = None
        await db.commit()
    return True


async def set_enabled(db: AsyncSession, org_id: str, channel_id: str, enabled: bool) -> Dict[str, Any]:
    ch = await _owned(db, org_id, channel_id)
    if enabled and ch.status == "disabled":
        ch.status = "active"
        ch.consecutive_failures = 0
    ch.enabled = bool(enabled)
    await db.commit()
    await db.refresh(ch)
    return public_view(ch)


async def delete_channel(db: AsyncSession, org_id: str, channel_id: str) -> None:
    ch = await _owned(db, org_id, channel_id)
    await db.delete(ch)
    await db.commit()


async def _owned(db: AsyncSession, org_id: str, channel_id: str) -> NotificationChannel:
    ch = (await db.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id, NotificationChannel.org_id == org_id)
    )).scalar_one_or_none()
    if ch is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ch


# ---------------------------------------------------------------------------
# Fan-out and delivery
# ---------------------------------------------------------------------------

async def alerts_sent_today(db: AsyncSession, org_id: str) -> int:
    midnight = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(await db.scalar(text(
        "SELECT count(*) FROM work_items WHERE org_id = :o AND kind = 'alert' AND created_at >= :m"
    ), {"o": org_id, "m": midnight}) or 0)


async def enqueue_alerts(db: AsyncSession, *, org_id: str, user_id: Optional[str], notification_id: str,
                         title: str, message: str, link: Optional[str]) -> int:
    """Queue one delivery per active channel. Over the daily cap: none queued."""
    from app.services.work_outbox import enqueue_work

    channels = [c for c in await list_channels(db, org_id) if c.enabled and c.status == "active"]
    if not channels:
        return 0
    limits = await alert_limits(db, org_id)
    room = limits["per_day"] - await alerts_sent_today(db, org_id)
    if room <= 0:
        logger.info("Alert cap reached for workspace %s; notification %s stays in-app only", org_id, notification_id)
        return 0
    queued = 0
    for ch in channels[:room]:
        await enqueue_work(
            db, kind="alert", job_id=f"{notification_id}:{ch.id}", org_id=org_id, user_id=user_id,
            payload={"channel_id": ch.id, "notification_id": notification_id, "title": title[:200],
                     "message": message[:3000], "link": link},
            idempotency_key=f"alert:{notification_id}:{ch.id}",
        )
        queued += 1
    return queued


def webhook_signature(secret: str, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def webhook_body(payload: Dict[str, Any]) -> bytes:
    link = payload.get("link")
    if link and link.startswith("/"):
        link = f"{settings.APP_BASE_URL.rstrip('/')}{link}"
    return json.dumps({
        "type": "helix.alert",
        "id": payload.get("notification_id"),
        "created_at": _now().isoformat(),
        "title": payload.get("title"),
        "message": payload.get("message"),
        "link": link,
    }, ensure_ascii=False, separators=(",", ":")).encode()


async def _send_webhook(config: Dict[str, Any], payload: Dict[str, Any]) -> None:
    from app.services.safe_fetch import safe_http_post_async

    body = webhook_body(payload)
    ts = str(int(_now().timestamp()))
    res = await safe_http_post_async(config["url"], body, headers={
        "Content-Type": "application/json", "User-Agent": "Helix-Alerts/1",
        "X-Helix-Timestamp": ts, "X-Helix-Signature": webhook_signature(config["secret"], ts, body),
    })
    if not 200 <= res.status_code < 300:
        raise RuntimeError(f"webhook answered HTTP {res.status_code}")


async def _send_telegram(config: Dict[str, Any], payload: Dict[str, Any]) -> None:
    link = payload.get("link")
    if link and link.startswith("/"):
        link = f"{settings.APP_BASE_URL.rstrip('/')}{link}"
    text_body = f"{payload.get('title') or 'Helix'}\n\n{payload.get('message') or ''}"
    if link:
        text_body += f"\n\n{link}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            f"{TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": config["chat_id"], "text": text_body[:4000], "disable_web_page_preview": True},
        )
    if res.status_code != 200:
        # Never include the URL: it carries the bot token.
        raise RuntimeError(f"telegram answered HTTP {res.status_code}")


async def deliver(org_id: str, payload: Dict[str, Any]) -> str:
    """Send one alert (work kind 'alert'). Raises on a failed send so the outbox retries."""
    from app.core.tenancy import apply_tenant_context, tenant_scope
    from app.db.session import async_session_maker
    from app.services.security_service import decrypt_secret

    channel_id = payload.get("channel_id")
    with tenant_scope([org_id], "", platform_admin=False, enforce=True):
        async with async_session_maker() as db:
            await apply_tenant_context(db)
            ch = (await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))).scalar_one_or_none()
            if ch is None or not ch.enabled or ch.status != "active" or not ch.config_encrypted:
                return "skipped"
            kind, config = ch.type, json.loads(decrypt_secret(ch.config_encrypted))
        error: Optional[str] = None
        try:
            if kind == "telegram":
                if not telegram_configured():
                    raise RuntimeError("telegram bot is not configured")
                await _send_telegram(config, payload)
            else:
                await _send_webhook(config, payload)
        except Exception as exc:  # recorded, then re-raised for the outbox retry
            error = str(exc)[:300] or type(exc).__name__
        disabled_now = False
        async with async_session_maker() as db:
            await apply_tenant_context(db)
            ch = (await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))).scalar_one_or_none()
            if ch is None:
                return "gone"
            if error is None:
                ch.last_success_at = _now()
                ch.consecutive_failures = 0
                ch.last_error = None
            else:
                ch.last_failure_at = _now()
                ch.last_error = error
                ch.consecutive_failures = int(ch.consecutive_failures or 0) + 1
                if ch.consecutive_failures >= settings.ALERT_MAX_CONSECUTIVE_FAILURES and ch.status == "active":
                    ch.status = "disabled"
                    disabled_now = True
            created_by, label = ch.created_by, ch.label
            await db.commit()
        if disabled_now:
            from app.services.notification_service import create_notification

            async with async_session_maker() as db:
                await apply_tenant_context(db)
                await create_notification(
                    db, user_id=created_by, org_id=org_id, type="warning", title="Alert channel turned off",
                    message=f"{label} failed {settings.ALERT_MAX_CONSECUTIVE_FAILURES} times in a row and was turned off. "
                            f"Last error: {error}. Fix it and turn it back on in Settings.",
                    link="/settings", fan_out=False,
                )
            return "disabled"
    if error is not None:
        raise RuntimeError(f"alert delivery failed: {error}")
    return "sent"
