import datetime
import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, String, func
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.core.config import settings

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


async def get_or_create_default_org(
    db: AsyncSession,
    user: User,
    lock_row: bool = False
) -> Organization:
    """
    Retrieves or creates the default organization for a user.
    Optionally applies a row-level lock (SELECT ... FOR UPDATE).
    Handles concurrent registration races via a nested savepoint and retry.
    """
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

    # 0. Administrator bypass: unrestricted features, unlimited credits
    if getattr(user, "role", None) == "admin":
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
                "ai_insights": True,
                "create_media": True,
                "deep_search": True,
                "advanced_scoring": True,
                "bulk_export": True,
                "custom_webhooks": True,
            }
        )
        return org, admin_plan

    # 1. Fetch Plan
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
    if not plan:
        from app.models.plan import Plan as PlanModel
        plan = PlanModel(
            id="plan_trial_default",
            name="7-Day Free Trial",
            type="trial",
            credit_allowance=50,
            daily_credit_limit=15.0,
            price_per_credit=0.0,
            feature_flags={
                "discover": True,
                "intelligence": True,
                "create": True,
                "performance": True,
                "swipe_files": True,
                "team_accounts": False,
                "public_api": False,
                "ai_insights": True,
                "create_media": True,
                "deep_search": True,
            }
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
                    "message": "Your 7-day free trial has expired. Upgrade your plan to continue using Helix Intelligence.",
                    "trial_expires_at": _format_iso(user.trial_expires_at),
                    "credit_balance": round(float(org.credit_balance), 2)
                }
            )

    # 3. Check Feature Flags
    if feature_name:
        active_flags = dict(plan.feature_flags or {})
        if org.custom_feature_flags:
            active_flags.update(org.custom_feature_flags)

        if not active_flags.get(feature_name, True):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "feature_disabled",
                    "message": f"The '{feature_name}' feature is disabled for your current plan.",
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


async def get_idempotent_operation(
    db: AsyncSession,
    org_id: str,
    idempotency_key: str,
    operation: Optional[str] = None
) -> Optional[UsageLog]:
    """Look up an existing operation by idempotency key to prevent double debiting (F10)."""
    if not idempotency_key or not org_id:
        return None
    stmt = select(UsageLog).where(
        UsageLog.org_id == org_id,
        cast(UsageLog.metadata_json, String).like(f'%"{idempotency_key}"%')
    )
    if operation:
        stmt = stmt.where(UsageLog.operation == operation)
    result = await db.execute(stmt)
    return result.scalars().first()


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
    if idempotency_key:
        existing = await get_idempotent_operation(db, org.id, idempotency_key, operation)
        if existing:
            return existing

    # 1. Row-lock and refresh the org with populate_existing=True
    lock_query = (
        select(Organization)
        .where(Organization.id == org.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_org = (await db.execute(lock_query)).scalar_one_or_none() or org

    meta = dict(metadata or {})
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key

    if amount > 0:
        if locked_org.credit_balance < amount:
            locked_org.status = "quota_exhausted"
            await db.commit()
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

    log_entry = UsageLog(
        org_id=locked_org.id,
        user_id=user_id or locked_org.owner_id,
        job_id=job_id,
        provider=provider,
        operation=operation,
        units=units,
        cost_usd=cost_usd,
        credits_deducted=amount,
        tokens_used=int(units) if "token" in operation else 0,
        requests_used=1,
        metadata_json=meta
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
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

    org.credit_balance += amount
    org.credits_used = max(0.0, org.credits_used - amount)
    org.daily_credits_used_today = max(0.0, org.daily_credits_used_today - amount)
    if org.status == "quota_exhausted" and org.credit_balance > 0:
        org.status = "active"

    refund_log = UsageLog(
        org_id=org.id,
        user_id=org.owner_id,
        job_id=job_id,
        provider="system",
        operation=f"refund_{reason}",
        units=1.0,
        cost_usd=0.0,
        credits_deducted=-amount,
        tokens_used=0,
        requests_used=0,
        metadata_json={"refund_reason": reason, "amount": amount}
    )
    db.add(refund_log)
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
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
    if not plan:
        from app.models.plan import Plan as PlanModel
        plan = PlanModel(
            id="plan_trial_default",
            name="7-Day Free Trial",
            type="trial",
            credit_allowance=25,
            daily_credit_limit=3.5,
            price_per_credit=0.0,
            feature_flags={
                "discover": True,
                "intelligence": True,
                "create": True,
                "performance": True,
                "swipe_files": True,
                "team_accounts": False,
                "public_api": False,
                "ai_insights": True,
                "create_media": True,
                "deep_search": True,
            }
        )

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

    # Video limits
    video_daily_limit = 3 if is_trial else 50
    if is_admin:
        video_daily_limit = 99999
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

    # 0. Administrator bypass
    if getattr(user, "role", None) == "admin":
        admin_plan = Plan(id="plan_admin", name="Admin", type="admin", credit_allowance=999999)
        return org, admin_plan

    # Fetch user plan
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    is_trial = (plan is None) or (plan.type == "trial") or (org.plan == "trial")

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

    # 3. Check 25-image total trial cap
    if is_trial and not is_video and total_used >= settings.TRIAL_IMAGES_TOTAL:
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

    # 4. Check Daily Video Limit on Paid Plans (F55)
    if is_video:
        daily_video_limit = (getattr(plan, "daily_video_limit", None) if plan else None) or 3
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
        return org, plan or Plan(id="plan_paid_default", name="Paid Plan", type="pay_as_you_go")

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

    return org, plan or Plan(id="plan_trial_default", name="7-Day Free Trial", type="trial")


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

