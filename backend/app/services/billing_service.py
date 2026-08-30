import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.core.config import settings

# Centralized Credit Costs
DISCOVER_SEARCH_CREDIT_COST = 2.0
DISCOVER_DEEP_SEARCH_CREDIT_COST = 3.0
CREATE_IMAGE_CREDIT_COST = 3.0
CREATE_VIDEO_CREDIT_COST = 8.0
ANALYSIS_PATTERN_CREDIT_COST = 1.0
AI_CHAT_CREDIT_COST = 0.5

CREDIT_COSTS: Dict[str, float] = {
    "discover_job": DISCOVER_SEARCH_CREDIT_COST,
    "discover_deep_fallback": DISCOVER_DEEP_SEARCH_CREDIT_COST,
    "create_image": CREATE_IMAGE_CREDIT_COST,
    "create_video": CREATE_VIDEO_CREDIT_COST,
    "ai_insight": ANALYSIS_PATTERN_CREDIT_COST,
    "pattern_pack": ANALYSIS_PATTERN_CREDIT_COST,
    "ai_chat": AI_CHAT_CREDIT_COST,
}

# Real cost mapping per provider unit in USD
ESTIMATED_PROVIDER_COSTS = {
    "groq_tokens": 0.0000006,       # ~$0.0006 per 1k tokens (Llama 3.3 70B)
    "brightdata_scrape": 0.003,     # ~$0.003 per page scrape request
    "scrapegraph_extract": 0.005,   # ~$0.005 per landing page extract
    "apify_ad": 0.00075,            # ~$0.75 per 1,000 ads
    "adyntel_query": 0.002,         # ~$0.002 per ad query
    "higgsfield_image": 0.02,       # ~$0.02 per image generation
    "higgsfield_video": 0.08,       # ~$0.08 per video generation
}


def _utc_midnight(dt: datetime.datetime) -> datetime.datetime:
    """Return the UTC midnight (00:00:00 UTC) for a given datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


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


async def get_or_create_default_org(
    db: AsyncSession,
    user: User,
    lock_row: bool = False
) -> Organization:
    """
    Retrieves or creates the default organization for a user.
    Optionally applies a row-level lock (SELECT ... FOR UPDATE).
    """
    query = select(Organization).where(Organization.owner_id == user.id)
    if lock_row:
        query = query.with_for_update()

    result = await db.execute(query)
    org = result.scalar_one_or_none()

    if not org:
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
                    "trial_expires_at": user.trial_expires_at.isoformat() + "Z",
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
    metadata: Optional[Dict[str, Any]] = None
) -> UsageLog:
    """
    Atomically deducts `amount` credits from org balance, increments counters,
    and creates a real UsageLog entry.
    """
    if amount > 0:
        org.credit_balance = max(0.0, org.credit_balance - amount)
        org.credits_used += amount
        await _ensure_daily_reset(db, org)
        org.daily_credits_used_today += amount
        if org.credit_balance <= 0.0:
            org.status = "quota_exhausted"

    log_entry = UsageLog(
        org_id=org.id,
        user_id=user_id or org.owner_id,
        job_id=job_id,
        provider=provider,
        operation=operation,
        units=units,
        cost_usd=cost_usd,
        credits_deducted=amount,
        tokens_used=int(units) if "token" in operation else 0,
        requests_used=1,
        metadata_json=metadata or {}
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
) -> None:
    """
    Restores credits to the organization when an asynchronous job fails
    before consuming external provider quota.
    """
    if amount <= 0:
        return

    result = await db.execute(
        select(Organization).where(Organization.id == org_id).with_for_update()
    )
    org = result.scalar_one_or_none()
    if org:
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

    return {
        "org_id": org.id,
        "org_name": org.name,
        "plan_id": plan.id,
        "plan_name": plan.name,
        "plan_type": plan.type,
        "credit_balance": round(float(org.credit_balance), 2),
        "credits_used": round(float(org.credits_used), 2),
        "status": org.status,
        "trial_expires_at": user.trial_expires_at.isoformat() + "Z" if user.trial_expires_at else None,
        "trial_days_remaining": trial_days_remaining,
        "daily_credit_limit": daily_limit,
        "daily_credits_used": daily_used,
        "daily_credits_remaining": daily_remaining,
        "daily_credits_resets_at_utc": daily_resets_at,
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
                "created_at": l.created_at.isoformat() + "Z" if l.created_at else ""
            }
            for l in logs
        ]
    }
