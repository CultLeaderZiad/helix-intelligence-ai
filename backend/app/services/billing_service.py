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

DISCOVER_SEARCH_CREDIT_COST = 2.0
ANALYSIS_PATTERN_CREDIT_COST = 1.0
AI_CHAT_CREDIT_COST = 0.5

# Real cost mapping per provider unit
ESTIMATED_PROVIDER_COSTS = {
    "groq_tokens": 0.0000006, # ~$0.0006 per 1k tokens (Llama 3.3 70B)
    "brightdata_scrape": 0.003, # ~$0.003 per page scrape request
    "scrapegraph_extract": 0.005, # ~$0.005 per landing page extract
    "apify_ad": 0.00075, # ~$0.75 per 1,000 ads
}

async def get_or_create_default_org(db: AsyncSession, user: User) -> Organization:
    result = await db.execute(select(Organization).where(Organization.owner_id == user.id))
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(
            name=f"{user.email.split('@')[0]}'s Workspace",
            owner_id=user.id,
            plan_id="plan_trial_default",
            plan="trial",
            credit_balance=25.0,
            credits_used=0.0,
            status="active"
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
    return org

async def check_quota_and_feature(
    db: AsyncSession,
    user: User,
    feature_name: str = "discover",
    required_credits: float = DISCOVER_SEARCH_CREDIT_COST
) -> Tuple[Organization, Plan]:
    """
    Real gatekeeper: checks 7-day trial expiration, feature flags, and credit balance.
    Raises clear HTTP 403 or 402 with structured error codes.
    """
    if settings.USE_MOCKS:
        # Pass mock checks
        mock_plan = Plan(id="plan_mock", name="Mock Plan", type="trial", credit_allowance=100, feature_flags={feature_name: True})
        mock_org = Organization(id="org_mock", name="Mock Org", owner_id=user.id, credit_balance=99.0, credits_used=1.0)
        return mock_org, mock_plan

    org = await get_or_create_default_org(db, user)

    # 1. Fetch Plan
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        # Fallback to default trial plan
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one()

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
                    "code": "TRIAL_EXPIRED",
                    "message": "Your 7-day free trial has expired. Upgrade your plan to continue researching creatives.",
                    "trial_expires_at": user.trial_expires_at.isoformat() + "Z",
                    "credit_balance": org.credit_balance
                }
            )

    # 3. Check Feature Flags
    active_flags = dict(plan.feature_flags or {})
    if org.custom_feature_flags:
        active_flags.update(org.custom_feature_flags)

    if not active_flags.get(feature_name, True):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FEATURE_DISABLED",
                "message": f"The '{feature_name}' feature is disabled for your current plan.",
                "feature": feature_name,
                "plan_name": plan.name
            }
        )

    # 4. Check Credit Balance Quota
    if org.credit_balance < required_credits:
        org.status = "quota_exhausted"
        await db.commit()
        raise HTTPException(
            status_code=402,
            detail={
                "code": "CREDIT_LIMIT_REACHED",
                "message": f"Insufficient credits ({org.credit_balance:.1f} available). This action requires {required_credits:.1f} credits. Add credits or upgrade your plan to continue.",
                "credit_balance": org.credit_balance,
                "credits_required": required_credits,
                "plan_name": plan.name
            }
        )

    return org, plan

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
    Atomically deducts credits from org balance, increments credits_used,
    and creates a real usage log entry.
    """
    # 1. Update organization balance
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org:
        org.credit_balance = max(0.0, org.credit_balance - credits_deducted)
        org.credits_used += credits_deducted
        if org.credit_balance <= 0.0:
            org.status = "quota_exhausted"

    # 2. Log usage
    log_entry = UsageLog(
        org_id=org_id,
        user_id=user_id,
        job_id=job_id,
        provider=provider,
        operation=operation,
        units=units,
        cost_usd=cost_usd,
        credits_deducted=credits_deducted,
        tokens_used=int(units) if "token" in operation else 0,
        requests_used=1,
        metadata_json=metadata or {}
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry

async def get_org_billing_summary(db: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Returns customer-facing billing & usage summary for the user's active organization.
    """
    org = await get_or_create_default_org(db, user)
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one()

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
        "feature_flags": plan.feature_flags or {},
        "recent_usage": [
            {
                "id": l.id,
                "provider": l.provider,
                "operation": l.operation,
                "units": l.units,
                "credits_deducted": l.credits_deducted,
                "cost_usd": l.cost_usd,
                "created_at": l.created_at.isoformat() + "Z" if l.created_at else ""
            }
            for l in logs
        ]
    }

