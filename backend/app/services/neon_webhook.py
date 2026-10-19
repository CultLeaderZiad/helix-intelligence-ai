"""Neon Auth (managed Better Auth) webhook verification.

Documented format: Ed25519 detached JWS over a double-base64url signing input,
with ``X-Neon-Timestamp`` bound into the payload. See
https://neon.com/docs/auth/guides/webhooks
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_jwks_keys
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from sqlalchemy import select

ACCEPTED_EVENTS = {
    "send.otp",
    "send.magic_link",
    "user.before_create",
    "user.created",
    "phone_number.verified",
    "organization.invitation.created",
    "organization.invitation.accepted",
}
TIMESTAMP_WINDOW_MS = 5 * 60 * 1000
FUTURE_SKEW_MS = 60 * 1000
_EVENT_ID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _header(headers: Mapping[str, str], name: str) -> str:
    # Starlette headers are case-insensitive; tests may pass a plain dict.
    if hasattr(headers, "get"):
        direct = headers.get(name)
        if direct:
            return str(direct).strip()
        lowered = headers.get(name.lower())
        if lowered:
            return str(lowered).strip()
    return ""


def _find_jwk(jwks: dict, kid: str) -> dict:
    for key in jwks.get("keys") or []:
        if key.get("kid") == kid and key.get("kty") == "OKP" and key.get("crv") == "Ed25519" and key.get("x"):
            return key
    raise HTTPException(status_code=401, detail="Invalid webhook signature")


def verify_detached_jws(body: bytes, signature: str, timestamp: str, jwk: dict) -> None:
    parts = signature.split(".")
    if len(parts) != 3 or parts[1] != "":
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    header_b64, _, signature_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "EdDSA":
            raise ValueError("alg")
        if jwk.get("kid") and header.get("kid") and header.get("kid") != jwk.get("kid"):
            raise ValueError("kid")
        payload_b64 = _b64url_encode(body)
        signature_payload = f"{timestamp}.{payload_b64}".encode("utf-8")
        signing_input = f"{header_b64}.{_b64url_encode(signature_payload)}".encode("ascii")
        public = Ed25519PublicKey.from_public_bytes(_b64url_decode(jwk["x"]))
        public.verify(_b64url_decode(signature_b64), signing_input)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from exc


def _check_timestamp(raw: str, now_ms: int | None = None) -> None:
    try:
        timestamp_ms = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from exc
    current = int(datetime.now(timezone.utc).timestamp() * 1000) if now_ms is None else now_ms
    if timestamp_ms > current + FUTURE_SKEW_MS or current - timestamp_ms > TIMESTAMP_WINDOW_MS:
        raise HTTPException(status_code=401, detail="Webhook timestamp is outside the allowed window")


def ack_for(event_type: str, event_id: str) -> dict[str, Any]:
    """Stable body for both the first delivery and a duplicate."""
    if event_type == "user.before_create":
        return {"allowed": True, "event_id": event_id, "status": "processed"}
    return {"ok": True, "event_id": event_id, "event_type": event_type, "status": "processed"}


async def verify_and_parse(body: bytes, headers: Mapping[str, str], *, jwks: dict | None = None, now_ms: int | None = None) -> dict:
    signature = _header(headers, "x-neon-signature")
    kid = _header(headers, "x-neon-signature-kid")
    timestamp = _header(headers, "x-neon-timestamp")
    event_id = _header(headers, "x-neon-event-id")
    event_type = _header(headers, "x-neon-event-type")
    if not signature or not kid or not timestamp or not event_id or not event_type:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if not _EVENT_ID.match(event_id):
        raise HTTPException(status_code=400, detail="Invalid webhook event id")
    if event_type not in ACCEPTED_EVENTS:
        raise HTTPException(status_code=400, detail="Unsupported webhook event")
    _check_timestamp(timestamp, now_ms=now_ms)
    if jwks is None:
        url = settings.NEON_AUTH_URL.rstrip("/") + "/.well-known/jwks.json"
        jwks = await get_jwks_keys(url)
        if not any(item.get("kid") == kid for item in (jwks.get("keys") or [])):
            jwks = await get_jwks_keys(url, unknown_kid=kid)
    jwk = _find_jwk(jwks, kid)
    verify_detached_jws(body, signature, timestamp, jwk)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    body_event_id = str(payload.get("event_id") or "")
    body_event_type = str(payload.get("event_type") or "")
    if body_event_id != event_id or body_event_type != event_type:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if event_type == "user.created":
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        if not user.get("id") or not user.get("email"):
            raise HTTPException(status_code=400, detail="Missing user id or email")
    payload["_verified_event_id"] = event_id
    payload["_verified_event_type"] = event_type
    return payload


async def _sync_created_user(db: AsyncSession, payload: dict) -> None:
    user = payload.get("user") or {}
    user_id = str(user.get("id"))
    email = str(user.get("email") or "").strip().lower()
    name = str(user.get("name") or "")
    existing = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if existing:
        return
    email_owner = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if email_owner:
        return
    now = datetime.now(timezone.utc)
    db.add(User(
        id=user_id,
        email=email,
        full_name=name or None,
        password_hash="EXTERNAL_AUTH_MANAGED",
        role="customer",
        signup_metadata={"token_version": 1},
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=int(settings.TRIAL_DAYS or 7)),
    ))
    await db.flush()
    from app.core.tenancy import apply_tenant_context, bind_tenant
    bind_tenant([], user_id, platform_admin=False, enforce=True)
    await apply_tenant_context(db)
    from app.services import billing_service
    created = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    org = await billing_service.get_or_create_default_org(db, created)
    bind_tenant([org.id], user_id, platform_admin=False, enforce=True)
    await apply_tenant_context(db)


async def process_auth_webhook(db: AsyncSession, payload: dict) -> dict[str, Any]:
    """Insert the event id once, then apply the event in the same transaction."""
    event_id = payload["_verified_event_id"]
    event_type = payload["_verified_event_type"]
    ack = ack_for(event_type, event_id)
    now = datetime.now(timezone.utc)
    stmt = pg_insert(WebhookEvent).values(
        id=str(uuid.uuid4()),
        request_id=event_id,
        event_id=event_id,
        provider="neon_auth",
        status="processed",
        payload={"event_type": event_type, "event_id": event_id},
        created_at=now,
        updated_at=now,
    ).on_conflict_do_nothing(
        constraint="uq_webhook_events_provider_event_id"
    ).returning(WebhookEvent.id)
    inserted = (await db.execute(stmt)).first()
    if inserted is None:
        await db.rollback()
        return ack
    if event_type == "user.created":
        await _sync_created_user(db, payload)
    await db.commit()
    return ack
