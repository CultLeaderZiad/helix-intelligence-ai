"""Whop billing: checkout links and the membership webhook.

Contract (Whop API v1, checked 2026-11-23):
- Webhooks follow Standard Webhooks. Whop HMAC-SHA256s
  ``{webhook-id}.{webhook-timestamp}.{raw body}`` with the literal bytes of the
  endpoint's ``ws_...`` secret and sends ``webhook-signature: v1,<base64>``
  (whop-sdk 2.8.1 ``lib/verify_webhook.py``). Requests more than 5 minutes
  from now are rejected. Delivery is at least once and unordered.
- ``POST /checkout_configurations`` takes ``variant_id`` (``plan_...``),
  ``redirect_url`` and ``metadata``; the metadata is copied to the payment and
  the membership, and ``purchase_url`` is the checkout link.
- Membership events (``membership.activated`` / ``membership.updated``) carry
  the membership: ``id``, ``status``, ``variant_id``, ``metadata``,
  ``current_period_end``, ``expires_at``, ``updated_at``. ``active``,
  ``trialing``, ``past_due`` (grace after a failed payment), ``canceling`` and
  ``completed`` keep access; ``canceled`` and ``expired`` do not.

Access is an ordinary organization_access_grants row created for the
workspace's owner, expiring at the paid period end plus WHOP_GRACE_HOURS, so a
missed cancellation still lapses on its own. Only grants this module created
are ever changed or revoked; an admin's grant is never touched.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import logging
from typing import Any, Dict, Mapping, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER = "whop"
ORG_METADATA_KEY = "helix_org_id"
TOLERANCE_SECONDS = 5 * 60
ACCESS_STATUSES = frozenset({"active", "trialing", "past_due", "canceling", "completed"})
ENDED_STATUSES = frozenset({"canceled", "expired"})
MEMBERSHIP_EVENTS = frozenset({"membership.activated", "membership.updated"})


class WebhookRejected(Exception):
    """The request is not a genuine, fresh Whop delivery."""


# ---------------------------------------------------------------------------
# Pure helpers (no database)
# ---------------------------------------------------------------------------

def configured_for_webhooks() -> bool:
    return bool((settings.WHOP_WEBHOOK_SECRET or "").strip())


def configured_for_checkout() -> bool:
    return bool((settings.WHOP_API_KEY or "").strip() and plan_map())


def plan_map(raw: Optional[str] = None) -> Dict[str, str]:
    """WHOP_PLAN_MAP "plan_a=helix_plan,plan_b=helix_plan" -> {plan_a: helix_plan}."""
    raw = settings.WHOP_PLAN_MAP if raw is None else raw
    out: Dict[str, str] = {}
    for part in (raw or "").split(","):
        whop_plan, sep, helix_plan = part.partition("=")
        whop_plan, helix_plan = whop_plan.strip(), helix_plan.strip()
        if sep and whop_plan and helix_plan:
            out[whop_plan] = helix_plan
    return out


def whop_plan_for(helix_plan_id: str) -> Optional[str]:
    for whop_plan, helix_plan in plan_map().items():
        if helix_plan == helix_plan_id:
            return whop_plan
    return None


def sign(secret: str, webhook_id: str, timestamp: str, body: bytes) -> str:
    """The v1 signature Whop sends. Used by verify() and by tests."""
    message = f"{webhook_id}.{timestamp}.".encode() + body
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def verify(body: bytes, headers: Mapping[str, str], secret: str, now: Optional[float] = None) -> str:
    """Return the webhook id of a genuine delivery, else raise WebhookRejected."""
    if not secret:
        raise WebhookRejected("no secret configured")
    lower = {str(k).lower(): v for k, v in headers.items()}
    webhook_id = (lower.get("webhook-id") or "").strip()
    timestamp = (lower.get("webhook-timestamp") or "").strip()
    signatures = (lower.get("webhook-signature") or "").strip()
    if not (webhook_id and timestamp and signatures):
        raise WebhookRejected("missing signature headers")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise WebhookRejected("bad timestamp") from exc
    current = datetime.datetime.now(datetime.timezone.utc).timestamp() if now is None else now
    if abs(current - sent_at) > TOLERANCE_SECONDS:
        raise WebhookRejected("timestamp outside tolerance")
    expected = sign(secret, webhook_id, timestamp, body)
    # The header may hold several space-separated "v1,<sig>" entries (key rotation).
    for candidate in signatures.split():
        if hmac.compare_digest(candidate.strip(), expected):
            return webhook_id
    raise WebhookRejected("no signature matches")


def _aware(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value


def _parse_time(value: Any) -> Optional[datetime.datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def access_until(membership: Dict[str, Any]) -> Optional[datetime.datetime]:
    """When paid access ends, plus the grace period. None = no end (one-time purchase)."""
    end = _parse_time(membership.get("current_period_end")) or _parse_time(membership.get("expires_at"))
    if end is None:
        return None
    return end + datetime.timedelta(hours=int(settings.WHOP_GRACE_HOURS))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

async def create_checkout(org_id: str, helix_plan_id: str, redirect_url: str) -> str:
    """A Whop checkout link for this workspace and plan. The workspace id rides
    in metadata, set here on the server from the caller's session, never from
    the browser."""
    import httpx

    if not configured_for_checkout():
        raise HTTPException(status_code=503, detail={"code": "billing_not_configured", "message": "Checkout is not available yet."})
    variant_id = whop_plan_for(helix_plan_id)
    if not variant_id:
        raise HTTPException(status_code=404, detail={"code": "plan_not_purchasable", "message": "This plan cannot be bought online."})
    body: Dict[str, Any] = {
        "variant_id": variant_id,
        "redirect_url": redirect_url,
        "metadata": {ORG_METADATA_KEY: org_id},
    }
    if settings.WHOP_COMPANY_ID:
        body["account_id"] = settings.WHOP_COMPANY_ID
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{settings.WHOP_API_BASE.rstrip('/')}/checkout_configurations",
                json=body,
                headers={"Authorization": f"Bearer {settings.WHOP_API_KEY}"},
            )
    except httpx.HTTPError as exc:
        logger.warning("whop checkout request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail={"code": "billing_provider_unavailable", "message": "Checkout is unavailable. Try again."})
    if res.status_code >= 300:
        logger.warning("whop checkout refused: HTTP %s", res.status_code)
        raise HTTPException(status_code=502, detail={"code": "billing_provider_unavailable", "message": "Checkout is unavailable. Try again."})
    url = (res.json() or {}).get("purchase_url")
    if not url:
        raise HTTPException(status_code=502, detail={"code": "billing_provider_unavailable", "message": "Checkout is unavailable. Try again."})
    return url


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

async def _record_delivery(db: AsyncSession, webhook_id: str, event: Dict[str, Any], status: str) -> bool:
    """Store the delivery once. False when this webhook id was already handled."""
    from app.models.webhook_event import WebhookEvent

    db.add(WebhookEvent(
        request_id=webhook_id,
        event_id=webhook_id,
        provider=PROVIDER,
        status=status,
        payload={"type": event.get("type"), "data_id": (event.get("data") or {}).get("id")},
    ))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False
    return True


async def handle_event(db: AsyncSession, webhook_id: str, event: Dict[str, Any]) -> str:
    """Apply one verified event. Returns what happened, for logs and tests.

    The delivery row and the access change commit together, so a retry after a
    crash re-applies cleanly and a duplicate is a no-op.
    """
    kind = str(event.get("type") or "")
    data = event.get("data") or {}
    if kind not in MEMBERSHIP_EVENTS or not isinstance(data, dict):
        # Payments and everything else are recorded only; access follows the membership.
        if not await _record_delivery(db, webhook_id, event, "ignored"):
            return "duplicate"
        await db.commit()
        return "ignored"

    org_id = str((data.get("metadata") or {}).get(ORG_METADATA_KEY) or "")
    membership_id = str(data.get("id") or "")
    if not org_id or not membership_id:
        if not await _record_delivery(db, webhook_id, event, "unlinked"):
            return "duplicate"
        await db.commit()
        logger.warning("whop membership %s has no %s; nothing granted", membership_id or "?", ORG_METADATA_KEY)
        return "unlinked"

    from app.core.tenancy import apply_tenant_context, tenant_scope

    with tenant_scope([org_id], "", platform_admin=False, enforce=True):
        await apply_tenant_context(db)
        if not await _record_delivery(db, webhook_id, event, "processed"):
            return "duplicate"
        await apply_tenant_context(db)
        outcome = await _apply_membership(db, org_id, membership_id, data)
        await db.commit()
    return outcome


async def _apply_membership(db: AsyncSession, org_id: str, membership_id: str, data: Dict[str, Any]) -> str:
    from app.models.access_grant import OrganizationAccessGrant
    from app.models.billing_subscription import BillingSubscription
    from app.models.organization import Organization
    from app.models.plan import Plan
    from app.models.usage_log import UsageLog
    from app.services.admin_service import GRANTABLE_FEATURES

    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if org is None:
        logger.warning("whop membership %s names unknown workspace", membership_id)
        return "unknown_workspace"

    status = str(data.get("status") or "")
    whop_plan = str(data.get("variant_id") or "")
    helix_plan_id = plan_map().get(whop_plan)
    updated_at = _parse_time(data.get("updated_at")) or datetime.datetime.now(datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)

    sub = (await db.execute(
        select(BillingSubscription).where(
            BillingSubscription.provider == PROVIDER,
            BillingSubscription.provider_membership_id == membership_id,
        )
    )).scalar_one_or_none()
    if sub is not None and sub.org_id != org_id:
        logger.warning("whop membership %s moved workspace; ignored", membership_id)
        return "workspace_mismatch"
    if sub is not None and sub.last_event_at is not None and updated_at < sub.last_event_at:
        return "stale"
    if sub is None:
        sub = BillingSubscription(org_id=org_id, provider=PROVIDER, provider_membership_id=membership_id, status=status)
        db.add(sub)
    previous_end = _aware(sub.current_period_end)
    sub.status = status
    sub.provider_plan_id = whop_plan or None
    sub.plan_id = helix_plan_id
    sub.last_event_at = updated_at
    sub.current_period_end = _parse_time(data.get("current_period_end")) or _parse_time(data.get("expires_at"))

    grant = None
    if sub.grant_id:
        grant = (await db.execute(
            select(OrganizationAccessGrant).where(OrganizationAccessGrant.id == sub.grant_id)
        )).scalar_one_or_none()

    def audit(operation: str, extra: Dict[str, Any]) -> None:
        db.add(UsageLog(
            org_id=org.id, user_id=org.owner_id, provider=PROVIDER, operation=operation,
            units=1.0, cost_usd=0.0, credits_deducted=0.0, requests_used=0,
            metadata_json={"membership_id": membership_id, "status": status, "whop_plan_id": whop_plan, **extra},
        ))

    if status in ACCESS_STATUSES:
        plan = None
        if helix_plan_id:
            plan = (await db.execute(select(Plan).where(Plan.id == helix_plan_id))).scalar_one_or_none()
        if plan is None:
            logger.warning("whop plan %s is not mapped to a Helix plan; nothing granted", whop_plan or "?")
            audit("billing_unmapped_plan", {})
            return "unmapped_plan"
        flags = {k: True for k, v in (plan.feature_flags or {}).items() if k in GRANTABLE_FEATURES and v}
        if not flags:
            logger.warning("Helix plan %s grants no features; nothing granted", plan.id)
            audit("billing_unmapped_plan", {"plan_id": plan.id})
            return "unmapped_plan"
        expires = access_until(data)
        if grant is not None and grant.revoked_at is None:
            grant.expires_at = expires
            grant.plan_id = plan.id
            grant.feature_flags = flags
        else:
            grant = OrganizationAccessGrant(
                org_id=org.id, plan_id=plan.id, feature_flags=flags,
                granted_by_user_id=org.owner_id, expires_at=expires,
            )
            db.add(grant)
            await db.flush()
            sub.grant_id = grant.id
        org.plan_id = plan.id
        org.plan = plan.type
        if org.status not in ("active", "suspended"):
            org.status = "active"
        # Searches and monitor runs spend credits, and credits are not renewed
        # anywhere else. Each new paid period resets the balance to the plan's
        # monthly allowance (unused credits do not roll over). A repeated event
        # for the same period changes nothing.
        new_end = _aware(sub.current_period_end)
        new_period = previous_end is None or (new_end is not None and new_end > previous_end)
        credits = None
        if new_period and plan.credit_allowance is not None:
            credits = float(plan.credit_allowance)
            org.credit_balance = credits
        audit("billing_access_granted", {"plan_id": plan.id, "expires_at": expires.isoformat() if expires else None,
                                         "credits_set_to": credits})
        return "granted"

    if status in ENDED_STATUSES:
        if grant is not None and grant.revoked_at is None:
            grant.revoked_at = now
            grant.revoked_by_user_id = org.owner_id
            audit("billing_access_revoked", {"grant_id": grant.id})
            return "revoked"
        return "already_ended"

    # drafted, unresolved or anything new: keep the current state.
    audit("billing_status_noted", {})
    return "noted"
