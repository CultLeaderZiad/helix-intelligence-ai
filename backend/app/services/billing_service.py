import datetime
import hashlib
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.models.credit_ledger import CreditLedgerEntry, CreditReservation, OperationIdempotency
from app.core.config import settings

_MONEY = Decimal("0.000001")
_ACTIVE_ORG_STATUSES = {"active", "quota_exhausted", "daily_limit_reached"}
_SECRET_FLAG_PARTS = ("api_key", "secret", "token", "password", "cookie")


def _decimal_amount(amount) -> Decimal:
    quantized = Decimal(str(amount if amount is not None else 0)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return quantized


def _payload_hash(operation: str, amount, job_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> str:
    body = {
        "operation": operation,
        "amount": str(_decimal_amount(amount)),
        "job_id": job_id,
        "metadata": metadata or {},
    }
    encoded = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _org_is_trial(org: Organization) -> bool:
    plan_name = (getattr(org, "plan", None) or "").lower()
    plan_id = getattr(org, "plan_id", None) or ""
    return plan_name == "trial" or plan_id.startswith("plan_trial")


def _is_secret_flag(name: str) -> bool:
    lowered = str(name or "").lower().replace("-", "_")
    return any(part in lowered for part in _SECRET_FLAG_PARTS)


def _merged_flags(plan: Plan, org: Organization) -> Dict[str, Any]:
    flags = dict(plan.feature_flags or {})
    for key, value in (org.custom_feature_flags or {}).items():
        if _is_secret_flag(key):
            continue
        flags[key] = value
    return flags


def is_platform_admin(user: User) -> bool:
    """Platform admin is an explicit flag or the existing admin role.

    Organization owners and assistant-admins are not platform admins.
    There is no email allowlist.
    """
    return bool(getattr(user, "is_platform_admin", False)) or getattr(user, "role", None) == "admin"


async def _latest_grant(db: AsyncSession, org_id: str):
    from app.models.access_grant import OrganizationAccessGrant

    return (
        await db.execute(
            select(OrganizationAccessGrant)
            .where(OrganizationAccessGrant.org_id == org_id)
            .order_by(OrganizationAccessGrant.granted_at.desc())
        )
    ).scalars().first()


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt


async def access_status_for_org(db: AsyncSession, org_id: str) -> Dict[str, Any]:
    """Honest access state. No grant is pending, not approved."""
    now = datetime.datetime.now(datetime.timezone.utc)
    grant = await _latest_grant(db, org_id)
    from app.models.access_grant import AccessRequest

    request_row = (
        await db.execute(
            select(AccessRequest)
            .where(AccessRequest.org_id == org_id)
            .order_by(AccessRequest.created_at.desc())
        )
    ).scalars().first()
    decision_at = None
    if grant is not None:
        # A future expiry is not a decision yet. Compare a later request to
        # the moment the grant actually stopped, or to when it was granted.
        if grant.revoked_at is not None:
            decision_at = _aware(grant.revoked_at)
        else:
            expires_at = _aware(grant.expires_at)
            if expires_at is not None and expires_at <= now:
                decision_at = expires_at
            else:
                decision_at = _aware(grant.granted_at)
    expires = _aware(grant.expires_at) if grant is not None else None
    grant_is_active = (
        grant is not None
        and grant.revoked_at is None
        and (expires is None or expires > now)
    )
    if grant_is_active:
        return {
            "status": "approved",
            "code": None,
            "message": "Access is approved.",
            "expires_at": expires.isoformat() if expires else None,
            "granted_at": grant.granted_at.isoformat() if grant.granted_at else None,
            "granted_by_user_id": grant.granted_by_user_id,
            "feature_flags": grant.feature_flags or {},
            "plan_id": grant.plan_id,
        }
    request_at = _aware(request_row.created_at) if request_row is not None else None
    request_is_later = (
        request_row is not None
        and request_at is not None
        and (decision_at is None or request_at > decision_at)
        and request_row.status in ("pending", "rejected")
    )
    if request_is_later and request_row.status == "rejected":
        return {
            "status": "rejected",
            "code": "access_rejected",
            "message": "The latest access request was rejected.",
        }
    if request_is_later and request_row.status == "pending":
        return {
            "status": "pending",
            "code": "access_pending_approval",
            "message": "Access is pending approval by a platform admin.",
        }
    if grant is not None and grant.revoked_at is None and expires is not None and expires <= now:
        return {
            "status": "expired",
            "code": "access_expired",
            "message": "Approved access has expired. Submit a new access request.",
            "expires_at": expires.isoformat(),
        }
    if grant is not None and grant.revoked_at is not None:
        return {
            "status": "revoked",
            "code": "access_revoked",
            "message": "Access was revoked. Workspace data is retained. Submit a new request if you still need access.",
        }
    if request_row is not None and request_row.status == "rejected":
        return {
            "status": "rejected",
            "code": "access_rejected",
            "message": "The latest access request was rejected.",
        }
    return {
        "status": "pending",
        "code": "access_pending_approval",
        "message": "Access is pending approval by a platform admin.",
    }


async def _require_active_grant(db: AsyncSession, org: Organization, user: User):
    """Platform admins operate without a workspace grant. Everyone else needs one."""
    if is_platform_admin(user) and not getattr(user, "_scoped_org_id", None):
        return None
    state = await access_status_for_org(db, org.id)
    if state["status"] != "approved":
        raise HTTPException(
            status_code=403,
            detail={
                "code": state["code"],
                "message": state["message"],
                "access_status": state["status"],
            },
        )
    return await _latest_grant(db, org.id)


def _explicit_limit(value, fallback: int) -> int:
    """None means 'use the documented fallback'. Zero is a real limit."""
    if value is None:
        return fallback
    return int(value)

# Centralized Credit Costs
DISCOVER_SEARCH_CREDIT_COST = 1.0
DISCOVER_DEEP_SEARCH_CREDIT_COST = 2.0
CREATE_IMAGE_CREDIT_COST = 2.0
CREATE_VIDEO_CREDIT_COST = 5.0
ANALYSIS_PATTERN_CREDIT_COST = 0.5
AI_CHAT_CREDIT_COST = 0.25
SIMULATION_CREDIT_COST = 1.0

CREDIT_COSTS: Dict[str, float] = {
    "discover_job": DISCOVER_SEARCH_CREDIT_COST,
    "discover_deep_fallback": DISCOVER_DEEP_SEARCH_CREDIT_COST,
    "create_image": CREATE_IMAGE_CREDIT_COST,
    "create_video": CREATE_VIDEO_CREDIT_COST,
    "ai_insight": ANALYSIS_PATTERN_CREDIT_COST,
    "pattern_pack": ANALYSIS_PATTERN_CREDIT_COST,
    "ai_chat": AI_CHAT_CREDIT_COST,
    "audience_simulation": SIMULATION_CREDIT_COST,
}

# Real cost mapping per provider unit in USD
ESTIMATED_PROVIDER_COSTS = {
    "groq_tokens": 0.0000006,       # ~$0.0006 per 1k tokens (Llama 3.3 70B)
    "brightdata_scrape": 0.003,     # ~$0.003 per page scrape request
    "scrapegraph_extract": 0.005,   # ~$0.005 per landing page extract
    "apify_ad": 0.00075,            # ~$0.75 per 1,000 ads
    "adyntel_query": 0.002,         # ~$0.002 per ad query
    "metapi_query": 0.001,          # Metapi free tier (est.)
}


def _utc_midnight(dt: datetime.datetime) -> datetime.datetime:
    """Return the UTC midnight (00:00:00 UTC) for a given datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _format_iso(dt: Optional[datetime.datetime]) -> Optional[str]:
    """Return a valid ISO-8601 string without double timezone suffixes."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat()


async def _ensure_daily_reset(db: AsyncSession, org: Organization) -> None:
    """
    If the org's daily counter hasn't been reset since the current UTC
    day began, zero it out and stamp the reset boundary.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    today_midnight = _utc_midnight(now)

    if org.daily_credits_reset_at is None or org.daily_credits_reset_at < today_midnight:
        org.daily_credits_used_today = 0.0
        org.daily_credits_reset_at = today_midnight
        await db.flush()


from sqlalchemy.exc import IntegrityError


async def resolve_active_org(db: AsyncSession, user: User) -> Optional[Organization]:
    """Pick the verified workspace for this caller.

    Order: API-key organization, explicit active workspace stored when an
    invite is accepted, a single paid membership when the caller's own
    organization is still a trial, then the owned organization, then the
    earliest membership. Several paid memberships and no explicit selection
    stay on the owned organization. Selecting among them needs the session
    organization id, which this wave cannot add.
    """
    scoped_org_id = getattr(user, "_scoped_org_id", None)
    if scoped_org_id:
        return (
            await db.execute(select(Organization).where(Organization.id == scoped_org_id))
        ).scalar_one_or_none()

    owned = (
        await db.execute(select(Organization).where(Organization.owner_id == user.id))
    ).scalars().first()

    from app.models.organization_member import OrganizationMember

    member_orgs = (
        await db.execute(
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.org_id)
            .where(OrganizationMember.user_id == user.id)
            .order_by(OrganizationMember.created_at.asc())
        )
    ).scalars().all()

    by_id: Dict[str, Organization] = {}
    if owned is not None:
        by_id[owned.id] = owned
    for org in member_orgs:
        by_id.setdefault(org.id, org)

    metadata = getattr(user, "signup_metadata", None) or {}
    active_id = metadata.get("active_org_id") if isinstance(metadata, dict) else None
    if active_id and active_id in by_id:
        return by_id[active_id]

    if owned is not None and _org_is_trial(owned):
        paid_memberships = [
            org for org in member_orgs
            if org.id != owned.id and not _org_is_trial(org) and (org.status or "active") == "active"
        ]
        if len(paid_memberships) == 1:
            return paid_memberships[0]
    if owned is not None:
        return owned
    return member_orgs[0] if member_orgs else None


async def get_or_create_default_org(
    db: AsyncSession,
    user: User,
    lock_row: bool = False
) -> Organization:
    """
    Retrieves or creates the default organization for a user.
    Optionally applies a row-level lock (SELECT ... FOR UPDATE).
    Handles concurrent registration races via a nested savepoint and retry.
    API-key callers are pinned to the key's organization before any owner lookup.
    """
    scoped_org_id = getattr(user, "_scoped_org_id", None)
    resolved = await resolve_active_org(db, user)
    if scoped_org_id and resolved is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "api_key_org_unavailable", "message": "API key organization is not available."},
        )
    if resolved is not None:
        if lock_row:
            resolved = (
                await db.execute(
                    select(Organization)
                    .where(Organization.id == resolved.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).scalar_one()
        await _ensure_daily_reset(db, resolved)
        return resolved

    query = select(Organization).where(Organization.owner_id == user.id)
    if lock_row:
        query = query.with_for_update().execution_options(populate_existing=True)

    result = await db.execute(query)
    org = result.scalar_one_or_none()

    if not org:
        # Check if user is a member of an existing organization (F46)
        from app.models.organization_member import OrganizationMember
        member_query = (
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.org_id)
            .where(OrganizationMember.user_id == user.id)
            .order_by(OrganizationMember.created_at.asc())
        )
        if lock_row:
            member_query = member_query.with_for_update().execution_options(populate_existing=True)
        member_org = (await db.execute(member_query)).scalars().first()
        if member_org:
            org = member_org
            await _ensure_daily_reset(db, org)
            return org

        created = False
        try:
            async with db.begin_nested():
                org = Organization(
                    name=f"{user.email.split('@')[0]}'s Workspace",
                    owner_id=user.id,
                    plan_id="plan_trial_default",
                    plan="trial",
                    credit_balance=25.0,
                    credits_used=0.0,
                    daily_credits_used_today=0.0,
                    status="active"
                )
                db.add(org)
                await db.flush()
                created = True
        except IntegrityError:
            # Another concurrent request already created the org
            query = select(Organization).where(Organization.owner_id == user.id)
            if lock_row:
                query = query.with_for_update().execution_options(populate_existing=True)
            result = await db.execute(query)
            org = result.scalar_one()

        if created:
            await db.commit()
            await db.refresh(org)
    else:
        await _ensure_daily_reset(db, org)
    return org


async def assert_can_spend(
    db: AsyncSession,
    user: User,
    required_credits: float = 1.0,
    feature_name: Optional[str] = None,
    lock_row: bool = True
) -> Tuple[Organization, Plan]:
    """
    Strict server-side gatekeeper.
    Performs atomic row-level lock on the organization, verifies 7-day trial expiration,
    checks feature flags, verifies daily limits, and validates credit balance.

    Raises:
      - 403: trial_expired or feature_disabled
      - 429: daily_limit_reached
      - 402: insufficient_credits
    """
    if settings.USE_MOCKS:
        org = await get_or_create_default_org(db, user, lock_row=False)
        mock_plan = Plan(
            id="plan_mock",
            name="Mock Plan",
            type="trial",
            credit_allowance=100,
            feature_flags={feature_name: True} if feature_name else {}
        )
        return org, mock_plan

    org = await get_or_create_default_org(db, user, lock_row=lock_row)

    # API-key scope is applied by get_or_create_default_org before this bypass.
    scoped_org_id = getattr(user, "_scoped_org_id", None)
    # 0. Administrator bypass: unrestricted features, unlimited credits
    if is_platform_admin(user) and not scoped_org_id:
        admin_plan = Plan(
            id="plan_admin",
            name="Helix Administrator",
            type="admin",
            credit_allowance=999999,
            daily_credit_limit=None,
            price_per_credit=0.0,
            feature_flags={
                "discover": True,
                "intelligence": True,
                "create": True,
                "performance": True,
                "swipe_files": True,
                "team_accounts": True,
                "public_api": True,
                "scout": True,
                "leadgen": True,
                "monitors": True,
                "ai_insights": True,
                "create_media": True,
                "deep_search": True,
                "advanced_scoring": True,
                "bulk_export": True,
                "custom_webhooks": True,
            }
        )
        return org, admin_plan

    # 1. Fetch Plan. A missing row is not a trial.
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_unavailable",
                "message": "This workspace has no plan record. Access is closed until a plan is assigned.",
                "plan_id": org.plan_id,
            },
        )

    if (org.status or "active") not in _ACTIVE_ORG_STATUSES:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_inactive",
                "message": "This workspace subscription is not active.",
                "status": org.status,
            },
        )

    # 2. Check 7-Day Trial Expiration
    now = datetime.datetime.now(datetime.timezone.utc)
    if plan.type == "trial" and user.trial_expires_at:
        trial_exp = user.trial_expires_at
        if trial_exp.tzinfo is None:
            trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
        if now > trial_exp:
            org.status = "trial_expired"
            await db.commit()
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "trial_expired",
                    "message": "The trial window has ended. A platform admin has to approve access before this workspace can continue.",
                    "trial_expires_at": _format_iso(user.trial_expires_at),
                    "credit_balance": round(float(org.credit_balance), 2)
                }
            )

    grant = await _require_active_grant(db, org, user)
    # 3. Check Feature Flags. A missing or empty flag is denied.
    if feature_name:
        active_flags = _merged_flags(plan, org)
        if grant is not None:
            active_flags.update(grant.feature_flags or {})
        if active_flags.get(feature_name) is not True:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "feature_disabled",
                    "message": f"The '{feature_name}' feature is not enabled for your current plan.",
                    "feature": feature_name,
                    "plan_name": plan.name
                }
            )

    # 4. Check Daily Credit Limit (UTC midnight boundary)
    daily_limit = getattr(plan, "daily_credit_limit", None)
    if daily_limit is not None and required_credits > 0:
        await _ensure_daily_reset(db, org)
        if (org.daily_credits_used_today + required_credits) > daily_limit:
            next_reset = _utc_midnight(now) + datetime.timedelta(days=1)
            reset_str = next_reset.strftime("%H:%M UTC")
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "daily_limit_reached",
                    "message": (
                        f"Daily credit limit reached ({daily_limit:.1f} credits/day). "
                        f"Used {org.daily_credits_used_today:.1f} of {daily_limit:.1f} credits today. "
                        f"Resets at {reset_str}. Upgrade or wait for trial reset."
                    ),
                    "daily_limit": daily_limit,
                    "daily_used": round(float(org.daily_credits_used_today), 2),
                    "daily_remaining": round(max(0.0, daily_limit - org.daily_credits_used_today), 2),
                    "resets_at_utc": next_reset.isoformat(),
                    "plan_name": plan.name
                }
            )

    # 5. Check Credit Balance Quota
    if required_credits > 0 and org.credit_balance < required_credits:
        org.status = "quota_exhausted"
        await db.commit()
        raise HTTPException(
            status_code=402,
            detail={
                "code": "insufficient_credits",
                "message": f"Not enough credits for this action ({org.credit_balance:.1f} available, {required_credits:.1f} required). Upgrade or wait for trial reset.",
                "credit_balance": round(float(org.credit_balance), 2),
                "required": required_credits,
                "plan_name": plan.name
            }
        )

    return org, plan


async def check_quota_and_feature(
    db: AsyncSession,
    user: User,
    feature_name: str = "discover",
    required_credits: float = DISCOVER_SEARCH_CREDIT_COST
) -> Tuple[Organization, Plan]:
    """Compatibility alias for assert_can_spend."""
    return await assert_can_spend(
        db,
        user=user,
        required_credits=required_credits,
        feature_name=feature_name,
        lock_row=True
    )


def _idempotency_key(value) -> Optional[str]:
    """Ignore unresolved header defaults when a route function is called directly."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


async def get_idempotent_operation(
    db: AsyncSession,
    org_id: str,
    idempotency_key: str,
    operation: Optional[str] = None
) -> Optional[UsageLog]:
    """Exact-match lookup. The key is a column, not a JSON substring."""
    idempotency_key = _idempotency_key(idempotency_key)
    if not idempotency_key or not org_id:
        return None
    stmt = select(UsageLog).where(
        UsageLog.org_id == org_id,
        UsageLog.idempotency_key == idempotency_key,
    )
    if operation:
        stmt = stmt.where(UsageLog.operation == operation)
    result = await db.execute(stmt)
    return result.scalars().first()


def _reject_payload_mismatch(existing: UsageLog, payload_hash: str) -> None:
    existing_hash = getattr(existing, "payload_hash", None) or (existing.metadata_json or {}).get("payload_hash")
    if existing_hash and existing_hash != payload_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "idempotency_payload_mismatch",
                "message": "This idempotency key was already used for a different payload.",
            },
        )


async def charge(
    db: AsyncSession,
    org: Organization,
    user_id: Optional[str],
    amount: float,
    provider: str,
    operation: str,
    units: float = 1.0,
    cost_usd: float = 0.0,
    job_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None
) -> UsageLog:
    """
    Atomically deducts `amount` credits from org balance, increments counters,
    and creates a real UsageLog entry.
    Locks and refreshes the organization row to avoid stale identity-map overwrites (F07).
    Idempotent: short-circuits if idempotency_key has already been charged (F10).
    """
    idempotency_key = _idempotency_key(idempotency_key)
    payload_hash = _payload_hash(operation, amount, job_id, metadata)
    meta = dict(metadata or {})
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key
    meta["payload_hash"] = payload_hash

    # 1. Row-lock the org before the idempotency read so concurrent retries serialize.
    lock_query = (
        select(Organization)
        .where(Organization.id == org.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_org = (await db.execute(lock_query)).scalar_one_or_none() or org

    if idempotency_key:
        existing = await get_idempotent_operation(db, locked_org.id, idempotency_key, operation)
        if existing:
            _reject_payload_mismatch(existing, payload_hash)
            return existing

    if amount > 0:
        if locked_org.credit_balance < amount:
            locked_org.status = "quota_exhausted"
            rollback = getattr(db, "rollback", None)
            if rollback:
                await rollback()
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": f"Not enough credits for this action ({locked_org.credit_balance:.1f} available, {amount:.1f} required).",
                    "credit_balance": round(float(locked_org.credit_balance), 2),
                    "required": amount,
                }
            )
        locked_org.credit_balance = max(0.0, locked_org.credit_balance - amount)
        locked_org.credits_used += amount
        await _ensure_daily_reset(db, locked_org)
        locked_org.daily_credits_used_today += amount
        if locked_org.credit_balance <= 0.0:
            locked_org.status = "quota_exhausted"

    from app.models.usage_log import generate_uuid as _new_id
    log_id = _new_id()
    reservation_id = _new_id()
    ledger_id = _new_id()
    decimal_amount = _decimal_amount(amount)
    log_entry = UsageLog(
        id=log_id,
        org_id=locked_org.id,
        user_id=user_id or locked_org.owner_id,
        job_id=job_id,
        provider=provider,
        operation=operation,
        units=units,
        cost_usd=cost_usd,
        credits_deducted=float(decimal_amount),
        tokens_used=int(units) if "token" in operation else 0,
        requests_used=1,
        metadata_json=meta,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
        reservation_id=reservation_id,
        ledger_id=ledger_id,
    )
    reservation = CreditReservation(
        id=reservation_id,
        org_id=locked_org.id,
        user_id=user_id or locked_org.owner_id,
        operation=operation,
        amount=decimal_amount,
        status="settled",
        job_id=job_id,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
        usage_log_id=log_id,
        settled_at=datetime.datetime.now(datetime.timezone.utc),
    )
    ledger = CreditLedgerEntry(
        id=ledger_id,
        org_id=locked_org.id,
        usage_log_id=log_id,
        reservation_id=reservation_id,
        entry_kind="debit",
        amount=decimal_amount,
        operation=operation,
        job_id=job_id,
    )
    db.add(log_entry)
    if hasattr(db, "flush"):
        await db.flush()
    db.add(reservation)
    db.add(ledger)
    if idempotency_key:
        db.add(OperationIdempotency(
            org_id=locked_org.id,
            operation=operation,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            job_id=job_id,
            usage_log_id=log_id,
            reservation_id=reservation_id,
        ))
    try:
        await db.commit()
    except IntegrityError:
        rollback = getattr(db, "rollback", None)
        if rollback:
            await rollback()
        existing = await get_idempotent_operation(db, locked_org.id, idempotency_key or "", operation)
        if existing:
            _reject_payload_mismatch(existing, payload_hash)
            return existing
        raise
    refresh = getattr(db, "refresh", None)
    if refresh:
        await refresh(log_entry)
    return log_entry


async def refund(
    db: AsyncSession,
    org_id: str,
    amount: float,
    reason: str,
    job_id: Optional[str] = None
) -> bool:
    """
    Restores credits to the organization when an asynchronous job fails
    before consuming external provider quota.
    Idempotent: prevents duplicate refunds for the same job_id (F08).
    """
    if amount <= 0:
        return False

    # 1. Lock organization with populate_existing=True (F07, F08)
    result = await db.execute(
        select(Organization)
        .where(Organization.id == org_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    org = result.scalar_one_or_none()
    if not org:
        return False

    # 2. Idempotency check: if job_id was already refunded, do not refund again (F08)
    reservation = None
    if job_id:
        existing_refund = (await db.execute(
            select(UsageLog).where(
                UsageLog.job_id == job_id,
                UsageLog.credits_deducted < 0
            )
        )).scalars().first()
        if existing_refund:
            logger.warning(f"Job {job_id} already has a refund recorded ({existing_refund.id}). Skipping duplicate refund.")
            return False
        reservation = (
            await db.execute(
                select(CreditReservation)
                .where(CreditReservation.job_id == job_id)
                .order_by(CreditReservation.created_at.desc())
            )
        ).scalars().first()
        if reservation is not None:
            if reservation.status == "refunded":
                return False
            if reservation.status == "settled":
                amount = float(reservation.amount)

    decimal_amount = _decimal_amount(amount)
    org.credit_balance += float(decimal_amount)
    org.credits_used = max(0.0, org.credits_used - float(decimal_amount))
    org.daily_credits_used_today = max(0.0, org.daily_credits_used_today - float(decimal_amount))
    if org.status == "quota_exhausted" and org.credit_balance > 0:
        org.status = "active"

    from app.models.usage_log import generate_uuid as _new_id
    refund_id = _new_id()
    ledger_id = _new_id()
    refund_log = UsageLog(
        id=refund_id,
        org_id=org.id,
        user_id=org.owner_id,
        job_id=job_id,
        provider="system",
        operation=f"refund_{reason}",
        units=1.0,
        cost_usd=0.0,
        credits_deducted=-float(decimal_amount),
        tokens_used=0,
        requests_used=0,
        metadata_json={"refund_reason": reason, "amount": float(decimal_amount)},
        ledger_id=ledger_id,
        reservation_id=reservation.id if reservation is not None else None,
    )
    db.add(refund_log)
    if hasattr(db, "flush"):
        await db.flush()
    db.add(CreditLedgerEntry(
        id=ledger_id,
        org_id=org.id,
        usage_log_id=refund_id,
        reservation_id=reservation.id if reservation is not None else None,
        entry_kind="refund",
        amount=decimal_amount,
        operation=f"refund_{reason}",
        job_id=job_id,
    ))
    if reservation is not None and reservation.status != "refunded":
        reservation.status = "refunded"
        reservation.settled_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return True


async def meter_and_deduct(
    db: AsyncSession,
    org_id: str,
    user_id: Optional[str],
    provider: str,
    operation: str,
    units: float,
    cost_usd: float,
    credits_deducted: float,
    job_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> UsageLog:
    """
    Compatibility function for older callers.
    """
    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id).with_for_update()
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise ValueError(f"Organization {org_id} not found")

    return await charge(
        db=db,
        org=org,
        user_id=user_id,
        amount=credits_deducted,
        provider=provider,
        operation=operation,
        units=units,
        cost_usd=cost_usd,
        job_id=job_id,
        metadata=metadata
    )


async def get_org_billing_summary(db: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Returns customer-facing billing & usage summary for the user's active organization.
    """
    org = await get_or_create_default_org(db, user)
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        return {
            "org_id": org.id,
            "org_name": org.name,
            "plan_id": org.plan_id,
            "plan_name": None,
            "plan_type": None,
            "plan_unavailable": True,
            "credit_balance": round(float(org.credit_balance), 2),
            "credits_used": round(float(org.credits_used), 2),
            "status": org.status,
            "subscription_lifecycle": "unconfigured",
            "renews_at": None,
            "feature_flags": {},
            "recent_usage": [],
            "billing_contract": "missing",
        }

    # Recent usage logs for this org
    logs_result = await db.execute(
        select(UsageLog)
        .where(UsageLog.org_id == org.id)
        .order_by(UsageLog.created_at.desc())
        .limit(25)
    )
    logs = logs_result.scalars().all()

    now = datetime.datetime.now(datetime.timezone.utc)
    trial_days_remaining = None
    if user.trial_expires_at:
        trial_exp = user.trial_expires_at
        if trial_exp.tzinfo is None:
            trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
        trial_days_remaining = max(0, (trial_exp - now).days) if trial_exp > now else 0

    daily_limit = getattr(plan, "daily_credit_limit", None)
    await _ensure_daily_reset(db, org)
    daily_used = round(float(org.daily_credits_used_today), 2)
    daily_remaining = round(max(0.0, (daily_limit or 0.0) - daily_used), 2) if daily_limit is not None else None
    daily_resets_at = None
    if daily_limit:
        daily_resets_at = (_utc_midnight(now) + datetime.timedelta(days=1)).isoformat()

    trial_summary = await get_trial_usage_summary(db, user, org)

    return {
        "org_id": org.id,
        "org_name": org.name,
        "plan_id": plan.id,
        "plan_name": plan.name,
        "plan_type": plan.type,
        "credit_balance": round(float(org.credit_balance), 2),
        "credits_used": round(float(org.credits_used), 2),
        "status": org.status,
        "access": await access_status_for_org(db, org.id),
        "subscription_lifecycle": "metered" if plan.type == "pay_as_you_go" else ("trial" if plan.type == "trial" else "admin_allocated"),
        "renews_at": None,
        "trial_expires_at": _format_iso(user.trial_expires_at),
        "trial_days_remaining": trial_days_remaining,
        "daily_credit_limit": daily_limit,
        "daily_credits_used": daily_used,
        "daily_credits_remaining": daily_remaining,
        "daily_credits_resets_at_utc": daily_resets_at,
        "trial_active": trial_summary["trial_active"],
        "images_used_today": trial_summary["images_used_today"],
        "images_daily_limit": trial_summary["images_daily_limit"],
        "images_remaining_today": trial_summary["images_remaining_today"],
        "images_trial_total": trial_summary["images_trial_total"],
        "requires_plan": trial_summary["requires_plan"],
        "feature_flags": plan.feature_flags or {},
        "recent_usage": [
            {
                "id": l.id,
                "provider": l.provider,
                "operation": l.operation,
                "units": l.units,
                "credits_deducted": l.credits_deducted,
                "cost_usd": l.cost_usd,
                "tokens_used": getattr(l, "tokens_used", 0),
                "created_at": _format_iso(l.created_at) or ""
            }
            for l in logs
        ]
    }


def is_trial_active(user: User) -> bool:
    """Returns True if the user is within their active 7-day trial window, or is an admin."""
    if getattr(user, "role", "") == "admin":
        return True
    if not user.trial_expires_at:
        return True
    now = datetime.datetime.now(datetime.timezone.utc)
    trial_exp = user.trial_expires_at
    if trial_exp.tzinfo is None:
        trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
    return now <= trial_exp


def get_trial_days_remaining(user: User) -> int:
    """Calculates remaining days in trial."""
    if getattr(user, "role", "") == "admin":
        return 999
    if not user.trial_expires_at:
        return settings.TRIAL_DAYS
    now = datetime.datetime.now(datetime.timezone.utc)
    trial_exp = user.trial_expires_at
    if trial_exp.tzinfo is None:
        trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
    if now > trial_exp:
        return 0
    delta = trial_exp - now
    return max(0, delta.days + (1 if delta.seconds > 0 else 0))


async def _ensure_daily_image_reset(db: AsyncSession, org: Organization) -> None:
    """Resets org.images_generated_today at UTC date boundaries."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    if org.images_today_date != today_str:
        org.images_generated_today = 0.0
        org.videos_generated_today = 0.0
        org.images_today_date = today_str
        await db.flush()


async def get_trial_usage_summary(db: AsyncSession, user: User, org: Optional[Organization] = None) -> Dict[str, Any]:
    """Returns normalized image usage metrics for trial/paid user."""
    if not org:
        org = await get_or_create_default_org(db, user, lock_row=False)
    else:
        await _ensure_daily_image_reset(db, org)

    is_admin = getattr(user, "role", None) == "admin"
    is_trial = org.plan == "trial" or bool(org.plan_id and org.plan_id.startswith("plan_trial"))
    active = is_trial_active(user)
    days_left = get_trial_days_remaining(user)

    daily_limit = settings.TRIAL_IMAGES_PER_DAY if is_trial else settings.PAID_IMAGES_PER_DAY
    if is_admin:
        daily_limit = 99999

    used_today = int(getattr(org, "images_generated_today", 0) or 0)
    remaining_today = max(0, daily_limit - used_today)
    total_used = int(getattr(org, "images_trial_total", 0) or 0)
    requires_plan = (not is_admin) and is_trial and (not active or total_used >= settings.TRIAL_IMAGES_TOTAL)

    # Video limits. Trial video is disabled. Zero on a plan stays zero.
    plan_row = None
    if org.plan_id:
        plan_row = (await db.execute(select(Plan).where(Plan.id == org.plan_id))).scalar_one_or_none()
    if is_admin:
        video_daily_limit = 99999
    elif is_trial:
        video_daily_limit = 0
    else:
        video_daily_limit = _explicit_limit(getattr(plan_row, "daily_video_limit", None) if plan_row else None, 0)
    videos_used_today = int(getattr(org, "videos_generated_today", 0) or 0)
    videos_remaining_today = max(0, video_daily_limit - videos_used_today)

    return {
        "trial_active": active if is_trial else True,
        "trial_days_remaining": days_left,
        "images_used_today": used_today,
        "images_daily_limit": daily_limit,
        "images_remaining_today": remaining_today,
        "images_trial_total": total_used,
        "videos_used_today": videos_used_today,
        "videos_daily_limit": video_daily_limit,
        "videos_remaining_today": videos_remaining_today,
        "trial_ends_at": _format_iso(user.trial_expires_at),
        "requires_plan": requires_plan
    }


async def assert_can_generate_image(
    db: AsyncSession,
    user: User,
    org: Optional[Organization] = None,
    media_type: str = "image",
    lock_row: bool = True
) -> Tuple[Organization, Plan]:
    """
    Strict server-side gatekeeper for Gemini Trial & Paid Media Generation (F11, F55).
    Guarantees:
    - 7-day trial expiry -> 402 HTTP (code: trial_expired)
    - Per-plan / trial daily image limits (with in-flight job reservation) -> 402 HTTP (code: daily_limit)
    - 25 total images cap on trial -> 402 HTTP (code: trial_total_limit)
    - Video on trial -> 402 HTTP (code: video_not_allowed)
    - Per-plan video limit on paid plans (with in-flight reservation) -> 402 HTTP (code: daily_video_limit)
    - Admin -> Bypass limitations
    """
    if not org:
        org = await get_or_create_default_org(db, user, lock_row=lock_row)
    else:
        await _ensure_daily_image_reset(db, org)

    # API-key scope wins before the administrator bypass.
    if getattr(user, "role", None) == "admin" and not getattr(user, "_scoped_org_id", None):
        admin_plan = Plan(id="plan_admin", name="Admin", type="admin", credit_allowance=999999)
        return org, admin_plan

    if (org.status or "active") not in _ACTIVE_ORG_STATUSES:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "subscription_inactive",
                "message": "This workspace subscription is not active.",
                "status": org.status,
            },
        )

    # Fetch user plan. A missing plan is not treated as a trial.
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_unavailable",
                "message": "This workspace has no plan record. Media generation is closed.",
                "plan_id": org.plan_id,
            },
        )
    await _require_active_grant(db, org, user)
    is_trial = (plan.type == "trial") or (org.plan == "trial")

    days_remaining = get_trial_days_remaining(user)
    used_today = int(getattr(org, "images_generated_today", 0) or 0)
    total_used = int(getattr(org, "images_trial_total", 0) or 0)
    is_video = media_type.lower() in ("video", "controlled_video", "before_after", "quick_video", "premium_video")

    # In-flight concurrent media jobs reservation check (F11)
    from app.models.media_job import MediaGenerationJob
    in_flight_count = 0
    try:
        if hasattr(db, "scalar"):
            in_flight_count = (await db.scalar(
                select(func.count(MediaGenerationJob.id)).where(
                    MediaGenerationJob.org_id == org.id,
                    MediaGenerationJob.status.in_(("pending", "running", "processing", "in_progress"))
                )
            )) or 0
        elif hasattr(db, "execute"):
            res = await db.execute(
                select(func.count(MediaGenerationJob.id)).where(
                    MediaGenerationJob.org_id == org.id,
                    MediaGenerationJob.status.in_(("pending", "running", "processing", "in_progress"))
                )
            )
            if hasattr(res, "scalar"):
                in_flight_count = res.scalar() or 0
    except Exception:
        in_flight_count = 0

    # 1. Video limit on trial (video requires a paid plan)
    if is_trial and is_video:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "video_not_allowed",
                "message": "Video generation is not available during the free trial. Please upgrade to a paid plan.",
                "trial_days_remaining": days_remaining
            }
        )

    # 2. Check 7-Day Trial Expiration
    if is_trial and not is_trial_active(user):
        org.status = "trial_expired"
        await db.commit()
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_expired",
                "message": "Your 7-day free trial has ended. Select a plan to continue creating AI ads.",
                "images_used_today": used_today,
                "images_daily_limit": settings.TRIAL_IMAGES_PER_DAY,
                "images_remaining_today": 0,
                "trial_days_remaining": 0
            }
        )

    # 3. Check 25-image total trial cap, including jobs that are not finished yet.
    if is_trial and not is_video and (total_used + in_flight_count) >= settings.TRIAL_IMAGES_TOTAL:
        org.status = "quota_exhausted"
        await db.commit()
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_total_limit",
                "message": f"You've reached your total trial allowance of {settings.TRIAL_IMAGES_TOTAL} images. Upgrade to continue creating.",
                "images_used_today": used_today,
                "images_daily_limit": settings.TRIAL_IMAGES_PER_DAY,
                "images_remaining_today": 0,
                "trial_days_remaining": days_remaining
            }
        )

    # 4. Check Daily Video Limit on Paid Plans (F55). Zero stays zero.
    if is_video:
        daily_video_limit = _explicit_limit(getattr(plan, "daily_video_limit", None), 0)
        videos_used_today = int(getattr(org, "videos_generated_today", 0) or 0)
        if (videos_used_today + in_flight_count) >= daily_video_limit:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "daily_video_limit",
                    "message": f"You've reached your daily limit of {daily_video_limit} videos (including in-flight jobs). Your quota resets at 00:00 UTC.",
                    "videos_used_today": videos_used_today,
                    "videos_in_flight": in_flight_count,
                    "daily_video_limit": daily_video_limit
                }
            )
        return org, plan

    # 5. Check Daily Image Limit (F55, F11)
    daily_limit = getattr(plan, "daily_image_limit", None) if plan else None
    if daily_limit is None:
        daily_limit = settings.TRIAL_IMAGES_PER_DAY if is_trial else settings.PAID_IMAGES_PER_DAY

    if (used_today + in_flight_count) >= daily_limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "daily_limit",
                "message": f"You've reached today's limit of {daily_limit} images (including in-flight jobs). Your quota resets at 00:00 UTC.",
                "images_used_today": used_today,
                "images_in_flight": in_flight_count,
                "images_daily_limit": daily_limit,
                "images_remaining_today": max(0, daily_limit - used_today - in_flight_count),
                "trial_days_remaining": days_remaining
            }
        )

    return org, plan


async def record_image_generated(
    db: AsyncSession,
    user: User,
    org: Organization,
    job_id: Optional[str] = None,
    cost_usd: float = 0.00
) -> UsageLog:
    """
    Increments daily and total image counters and logs usage under row-lock (F11).
    """
    lock_query = (
        select(Organization)
        .where(Organization.id == org.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_org = (await db.execute(lock_query)).scalar_one_or_none() or org
    await _ensure_daily_image_reset(db, locked_org)
    locked_org.images_generated_today = (getattr(locked_org, "images_generated_today", 0) or 0) + 1.0
    locked_org.images_trial_total = (getattr(locked_org, "images_trial_total", 0) or 0) + 1.0

    log = UsageLog(
        org_id=locked_org.id,
        user_id=user.id,
        job_id=job_id,
        provider="gemini",
        operation="media_generate_image",
        units=1.0,
        cost_usd=cost_usd,
        credits_deducted=0.0,
        requests_used=1,
        metadata_json={
            "images_generated_today": int(locked_org.images_generated_today),
            "images_trial_total": int(locked_org.images_trial_total)
        }
    )
    db.add(log)
    await db.commit()
    await db.refresh(locked_org)
    return log


async def record_video_generated(
    db: AsyncSession,
    user: User,
    org: Organization,
    job_id: Optional[str] = None,
    cost_usd: float = 0.00
) -> UsageLog:
    """
    Increments daily video counter and logs usage under row-lock (F11).
    """
    lock_query = (
        select(Organization)
        .where(Organization.id == org.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_org = (await db.execute(lock_query)).scalar_one_or_none() or org
    await _ensure_daily_image_reset(db, locked_org)
    locked_org.videos_generated_today = (getattr(locked_org, "videos_generated_today", 0) or 0) + 1.0

    log = UsageLog(
        org_id=locked_org.id,
        user_id=user.id,
        job_id=job_id,
        provider="pollinations",
        operation="media_generate_video",
        units=1.0,
        cost_usd=cost_usd,
        credits_deducted=0.0,
        requests_used=1,
        metadata_json={
            "videos_generated_today": int(locked_org.videos_generated_today),
        }
    )
    db.add(log)
    await db.commit()
    await db.refresh(locked_org)
    return log

