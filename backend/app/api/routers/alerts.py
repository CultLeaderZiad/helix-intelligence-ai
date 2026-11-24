"""Alert channels (Telegram, signed webhooks) and the Telegram bot webhook."""
import hmac
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import account_rate_limit, get_current_user, get_db
from app.models.user import User
from app.services import alert_channels, billing_service

logger = logging.getLogger(__name__)
router = APIRouter()
telegram_router = APIRouter()

_write_limit = Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))


async def _owner_org(db: AsyncSession, user: User):
    org = await billing_service.get_or_create_default_org(db, user)
    if org.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "owner_only", "message": "Only the workspace owner can change alert channels."})
    return org


@router.get("")
async def list_alert_channels(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = await billing_service.get_or_create_default_org(db, current_user)
    limits = await alert_channels.alert_limits(db, org.id)
    return {
        "items": [alert_channels.public_view(c) for c in await alert_channels.list_channels(db, org.id)],
        "limits": limits,
        "sent_today": await alert_channels.alerts_sent_today(db, org.id),
        "telegram_available": alert_channels.telegram_configured(),
    }


class WebhookCreate(BaseModel):
    url: str = Field(min_length=10, max_length=2048)


@router.post("/webhook", status_code=201, dependencies=[_write_limit])
async def add_webhook(body: WebhookCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = await _owner_org(db, current_user)
    return await alert_channels.create_webhook(db, org.id, current_user.id, body.url)


@router.post("/telegram", status_code=201, dependencies=[_write_limit])
async def link_telegram(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = await _owner_org(db, current_user)
    return await alert_channels.start_telegram_link(db, org.id, current_user.id)


class ChannelToggle(BaseModel):
    enabled: bool


@router.patch("/{channel_id}", dependencies=[_write_limit])
async def toggle_channel(channel_id: str, body: ChannelToggle, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    org = await _owner_org(db, current_user)
    return await alert_channels.set_enabled(db, org.id, channel_id, body.enabled)


@router.delete("/{channel_id}", dependencies=[_write_limit])
async def remove_channel(channel_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = await _owner_org(db, current_user)
    await alert_channels.delete_channel(db, org.id, channel_id)
    return {"ok": True}


@telegram_router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Telegram bot updates. Verified with the secret_token given to setWebhook."""
    expected = settings.TELEGRAM_WEBHOOK_SECRET or ""
    sent = request.headers.get("x-telegram-bot-api-secret-token") or ""
    if not expected or not alert_channels.telegram_configured():
        raise HTTPException(status_code=503, detail={"code": "telegram_not_configured"})
    if not hmac.compare_digest(sent.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail={"code": "invalid_secret"})
    try:
        update = await request.json()
    except ValueError:
        return {"ok": True}
    message = (update or {}).get("message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    if not text.startswith("/start ") or "id" not in chat:
        return {"ok": True}  # Telegram retries non-2xx; ignore everything else quietly.
    code = text.split(" ", 1)[1].strip()[:64]
    title = str(chat.get("title") or chat.get("username") or chat.get("first_name") or "")
    linked = await alert_channels.complete_telegram_link(db, code, int(chat["id"]), title)
    reply = ("Linked. Helix alerts for your workspace will arrive here." if linked
             else "This link has expired or was already used. Create a new one in Helix settings.")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{alert_channels.TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                              json={"chat_id": chat["id"], "text": reply})
    except httpx.HTTPError:
        logger.warning("telegram confirmation reply failed")
    return {"ok": True, "linked": linked}
