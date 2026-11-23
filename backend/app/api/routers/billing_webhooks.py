"""Inbound billing provider webhooks. No user session: the signature is the auth."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.services import whop_billing

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/whop")
async def whop_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not whop_billing.configured_for_webhooks():
        raise HTTPException(status_code=503, detail={"code": "billing_not_configured"})
    body = await request.body()
    try:
        webhook_id = whop_billing.verify(body, request.headers, settings.WHOP_WEBHOOK_SECRET)
    except whop_billing.WebhookRejected as exc:
        logger.warning("whop webhook rejected: %s", exc)
        raise HTTPException(status_code=401, detail={"code": "invalid_signature"})
    try:
        event = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "invalid_body"})
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail={"code": "invalid_body"})
    outcome = await whop_billing.handle_event(db, webhook_id, event)
    logger.info("whop webhook %s %s: %s", webhook_id, event.get("type"), outcome)
    return {"ok": True, "outcome": outcome}
