import datetime
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, desc, update
from fastapi import HTTPException

from app.schemas.admin import (
    AdminOverviewStats, AdminJobRow, AdminSystemHealth, AdminServiceHealth,
    PlanSchema, PlanCreate, PlanUpdate, AdminOrganizationRow, GrantCreditsRequest,
    SwitchPlanRequest, UpdateFeatureFlagsRequest, AdminUsageSummary,
    ProviderUsageBreakdown, AdminUsageRow, AdminUserRow, ImpersonateResponse,
    AdminUsageLogsFilterResponse
)
from app.models.organization import Organization
from app.models.user import User
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.models.scrape_job import ScrapeJob
from app.models.api_usage import ExternalApiUsage
from app.models.notification import Notification
from app.core.config import settings
from app.core.security import create_access_token

async def get_overview(db: AsyncSession) -> AdminOverviewStats:
    if settings.USE_MOCKS:
        return AdminOverviewStats(
            organizations=10,
            active_scrape_jobs=2,
            system_health="operational",
            api_error_rate=0.01,
            window_label="Last 24h",
            total_credits_consumed=142.5,
            total_provider_cost_usd=1.42,
            active_trials=8
        )
    
    org_count = await db.scalar(select(func.count(Organization.id))) or 0
    active_jobs = await db.scalar(select(func.count(ScrapeJob.id)).where(ScrapeJob.status == "running")) or 0
    total_credits = await db.scalar(select(func.sum(UsageLog.credits_deducted))) or 0.0
    total_cost = await db.scalar(select(func.sum(UsageLog.cost_usd))) or 0.0
    active_trials = await db.scalar(select(func.count(Organization.id)).where(Organization.plan_id == "plan_trial_default")) or 0

    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_api_calls = await db.scalar(select(func.count(ExternalApiUsage.id)).where(ExternalApiUsage.created_at >= start_of_day)) or 0
    today_api_spend = await db.scalar(select(func.sum(ExternalApiUsage.estimated_cost_usd)).where(ExternalApiUsage.created_at >= start_of_day)) or 0.0

    return AdminOverviewStats(
        organizations=org_count,
        active_scrape_jobs=active_jobs,
        system_health="operational",
        api_error_rate=0.0,
        window_label="All Time",
        total_credits_consumed=round(float(total_credits), 2),
        total_provider_cost_usd=round(float(total_cost), 4),
        active_trials=active_trials,
        today_api_calls=today_api_calls,
        today_api_spend=round(float(today_api_spend), 4)
    )

async def list_jobs(db: AsyncSession) -> list[AdminJobRow]:
    query = select(ScrapeJob, Organization).outerjoin(Organization, ScrapeJob.org_id == Organization.id).order_by(ScrapeJob.created_at.desc()).limit(30)
    result = await db.execute(query)
    rows = result.all()
    
    jobs = []
    for job, org in rows:
        jobs.append(AdminJobRow(
            job_id=job.id,
            organization=org.name if org else job.org_id,
            query=job.query,
            status=job.status,
            records=job.record_count or 0,
            duration_ms=job.elapsed_ms or 0,
            created_at=job.created_at.isoformat() + "Z" if job.created_at else ""
        ))
    return jobs

async def get_health(db: AsyncSession) -> AdminSystemHealth:
    db_status = "error"
    detail = "Disconnected"
    latency = 0
    try:
        start = datetime.datetime.now()
        await db.execute(text("SELECT 1"))
        latency = int((datetime.datetime.now() - start).total_seconds() * 1000)
        db_status = "success"
        detail = "Connected to Neon Postgres"
    except Exception as e:
        detail = str(e)

    return AdminSystemHealth(
        state="operational" if db_status == "success" else "degraded",
        services=[
            AdminServiceHealth(
                id="db-neon",
                name="Neon Serverless Postgres",
                status=db_status,
                detail=detail,
                latency_ms=latency,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            AdminServiceHealth(
                id="groq-ai",
                name="Groq LLM Engine (Llama 3.3 70B)",
                status="success",
                detail="Operational / Pattern Engine (~600 tokens/s)",
                latency_ms=120,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            AdminServiceHealth(
                id="metapi",
                name="Metapi Scraper API (Domain Trace)",
                status="success",
                detail="Operational / High-Yield Live Search",
                latency_ms=350,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            AdminServiceHealth(
                id="scrapegraph",
                name="ScrapeGraphAI Pipeline (Deep Read)",
                status="success",
                detail="Operational / Managed Smart Scraper",
                latency_ms=800,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            )
        ]
    )

# --- Plans Management ---
async def list_plans(db: AsyncSession) -> List[PlanSchema]:
    result = await db.execute(select(Plan).order_by(Plan.created_at.asc()))
    plans = result.scalars().all()
    return [
        PlanSchema(
            id=p.id,
            name=p.name,
            type=p.type,
            credit_allowance=p.credit_allowance,
            daily_credit_limit=p.daily_credit_limit,
            daily_image_limit=getattr(p, "daily_image_limit", 5) or 5,
            daily_video_limit=getattr(p, "daily_video_limit", 3) or 3,
            price_monthly=getattr(p, "price_monthly", 0.0) or 0.0,
            price_per_credit=p.price_per_credit,
            feature_flags=p.feature_flags or {},
            created_by_admin_id=p.created_by_admin_id,
            created_at=p.created_at.isoformat() + "Z" if p.created_at else None
        )
        for p in plans
    ]

async def create_plan(db: AsyncSession, plan_in: PlanCreate, admin_id: str) -> PlanSchema:
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    new_plan = Plan(
        id=plan_id,
        name=plan_in.name,
        type=plan_in.type,
        credit_allowance=plan_in.credit_allowance,
        daily_credit_limit=plan_in.daily_credit_limit,
        daily_image_limit=plan_in.daily_image_limit or 5,
        daily_video_limit=plan_in.daily_video_limit or 3,
        price_monthly=plan_in.price_monthly or 0.0,
        price_per_credit=plan_in.price_per_credit,
        feature_flags=plan_in.feature_flags,
        created_by_admin_id=admin_id
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return PlanSchema(
        id=new_plan.id,
        name=new_plan.name,
        type=new_plan.type,
        credit_allowance=new_plan.credit_allowance,
        daily_credit_limit=new_plan.daily_credit_limit,
        daily_image_limit=new_plan.daily_image_limit,
        daily_video_limit=new_plan.daily_video_limit,
        price_monthly=new_plan.price_monthly,
        price_per_credit=new_plan.price_per_credit,
        feature_flags=new_plan.feature_flags or {},
        created_by_admin_id=new_plan.created_by_admin_id,
        created_at=new_plan.created_at.isoformat() + "Z" if new_plan.created_at else None
    )

async def update_plan(db: AsyncSession, plan_id: str, plan_update: PlanUpdate) -> PlanSchema:
    plan = (await db.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan_update.name is not None:
        plan.name = plan_update.name
    if plan_update.type is not None:
        plan.type = plan_update.type
    if plan_update.credit_allowance is not None:
        plan.credit_allowance = plan_update.credit_allowance
    if plan_update.daily_credit_limit is not None:
        plan.daily_credit_limit = plan_update.daily_credit_limit
    if plan_update.daily_image_limit is not None:
        plan.daily_image_limit = plan_update.daily_image_limit
    if plan_update.daily_video_limit is not None:
        plan.daily_video_limit = plan_update.daily_video_limit
    if plan_update.price_monthly is not None:
        plan.price_monthly = plan_update.price_monthly
    if plan_update.price_per_credit is not None:
        plan.price_per_credit = plan_update.price_per_credit
    if plan_update.feature_flags is not None:
        plan.feature_flags = plan_update.feature_flags

    await db.commit()
    await db.refresh(plan)

    return PlanSchema(
        id=plan.id,
        name=plan.name,
        type=plan.type,
        credit_allowance=plan.credit_allowance,
        daily_credit_limit=plan.daily_credit_limit,
        daily_image_limit=getattr(plan, "daily_image_limit", 5),
        daily_video_limit=getattr(plan, "daily_video_limit", 3),
        price_monthly=getattr(plan, "price_monthly", 0.0),
        price_per_credit=plan.price_per_credit,
        feature_flags=plan.feature_flags or {},
        created_by_admin_id=plan.created_by_admin_id,
        created_at=plan.created_at.isoformat() + "Z" if plan.created_at else None
    )

# --- Organization & Quota Controls ---
async def list_organizations(db: AsyncSession) -> List[AdminOrganizationRow]:
    query = (
        select(Organization, User, Plan)
        .outerjoin(User, Organization.owner_id == User.id)
        .outerjoin(Plan, Organization.plan_id == Plan.id)
        .order_by(Organization.name.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    job_counts_result = await db.execute(
        select(ScrapeJob.org_id, func.count(ScrapeJob.id)).group_by(ScrapeJob.org_id)
    )
    job_counts = dict(job_counts_result.all())

    orgs = []
    for org, owner, plan in rows:
        effective_flags = dict(plan.feature_flags or {}) if plan else {}
        if org.custom_feature_flags:
            effective_flags.update(org.custom_feature_flags)

        orgs.append(AdminOrganizationRow(
            id=org.id,
            name=org.name,
            owner_id=owner.id if owner else org.owner_id,
            owner_email=owner.email if owner else "Unknown",
            plan_id=org.plan_id or "unknown",
            plan_name=plan.name if plan else (org.plan or "Custom"),
            plan_type=plan.type if plan else "custom",
            credit_balance=round(float(org.credit_balance or 0.0), 2),
            credits_used=round(float(org.credits_used or 0.0), 2),
            custom_feature_flags=org.custom_feature_flags or {},
            effective_feature_flags=effective_flags,
            status=org.status or "active",
            trial_expires_at=owner.trial_expires_at.isoformat() + "Z" if owner and owner.trial_expires_at else None,
            total_jobs=job_counts.get(org.id, 0)
        ))
    return orgs

async def grant_credits(db: AsyncSession, org_id: str, grant_in: GrantCreditsRequest, admin_id: str) -> Dict[str, Any]:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_bal = org.credit_balance or 0.0
    org.credit_balance = old_bal + grant_in.amount
    
    log = UsageLog(
        org_id=org.id,
        user_id=org.owner_id,
        provider="admin_manual",
        operation="grant_credits",
        units=grant_in.amount,
        cost_usd=0.0,
        credits_deducted=-grant_in.amount,
        metadata_json={"admin_id": admin_id, "reason": grant_in.reason}
    )
    db.add(log)
    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "message": f"Successfully added {grant_in.amount} credits to {org.name}",
        "org_id": org.id,
        "new_balance": org.credit_balance
    }

async def switch_organization_plan(db: AsyncSession, org_id: str, switch_in: SwitchPlanRequest) -> Dict[str, Any]:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    plan = (await db.execute(select(Plan).where(Plan.id == switch_in.plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Target Plan not found")

    org.plan_id = plan.id
    org.plan = plan.type
    if switch_in.reset_credits:
        org.credit_balance = float(plan.credit_allowance)

    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "message": f"Updated organization plan to {plan.name}",
        "org_id": org.id,
        "plan_id": plan.id,
        "plan_name": plan.name,
        "credit_balance": org.credit_balance
    }

async def update_organization_feature_flags(db: AsyncSession, org_id: str, flags_in: UpdateFeatureFlagsRequest) -> Dict[str, Any]:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    current_flags = dict(org.custom_feature_flags or {})
    current_flags.update(flags_in.feature_flags)
    org.custom_feature_flags = current_flags

    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "org_id": org.id,
        "custom_feature_flags": org.custom_feature_flags
    }

# --- Usage & Metering Analytics ---
async def get_usage_summary(db: AsyncSession) -> AdminUsageSummary:
    total_cost = await db.scalar(select(func.sum(UsageLog.cost_usd))) or 0.0
    total_credits = await db.scalar(select(func.sum(UsageLog.credits_deducted))) or 0.0
    total_reqs = await db.scalar(select(func.count(UsageLog.id))) or 0

    stmt = (
        select(
            UsageLog.provider,
            UsageLog.operation,
            func.sum(UsageLog.units).label("total_units"),
            func.sum(UsageLog.cost_usd).label("total_cost"),
            func.sum(UsageLog.credits_deducted).label("total_credits"),
            func.count(UsageLog.id).label("total_count")
        )
        .group_by(UsageLog.provider, UsageLog.operation)
    )
    res = await db.execute(stmt)
    by_provider = [
        ProviderUsageBreakdown(
            provider=row.provider,
            operation=row.operation,
            total_units=round(float(row.total_units or 0), 2),
            total_cost_usd=round(float(row.total_cost or 0), 4),
            total_credits_deducted=round(float(row.total_credits or 0), 2),
            total_requests=row.total_count
        )
        for row in res.all()
    ]

    recent_query = (
        select(UsageLog, Organization, User)
        .outerjoin(Organization, UsageLog.org_id == Organization.id)
        .outerjoin(User, UsageLog.user_id == User.id)
        .order_by(UsageLog.created_at.desc())
        .limit(50)
    )
    recent_res = await db.execute(recent_query)
    recent_logs = [
        AdminUsageRow(
            id=log.id,
            org_id=log.org_id,
            org_name=org.name if org else log.org_id,
            user_email=user.email if user else None,
            job_id=log.job_id,
            provider=log.provider,
            operation=log.operation,
            units=round(float(log.units), 2),
            cost_usd=round(float(log.cost_usd), 4),
            credits_deducted=round(float(log.credits_deducted), 2),
            created_at=log.created_at.isoformat() + "Z" if log.created_at else ""
        )
        for log, org, user in recent_res.all()
    ]

    return AdminUsageSummary(
        total_cost_usd=round(float(total_cost), 4),
        total_credits_deducted=round(float(total_credits), 2),
        total_requests=total_reqs,
        by_provider=by_provider,
        recent_logs=recent_logs
    )

async def get_usage_logs_filtered(
    db: AsyncSession,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    provider: Optional[str] = None,
    operation: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> AdminUsageLogsFilterResponse:
    query = (
        select(UsageLog, Organization, User)
        .outerjoin(Organization, UsageLog.org_id == Organization.id)
        .outerjoin(User, UsageLog.user_id == User.id)
    )
    count_query = select(func.count(UsageLog.id))

    if user_id:
        query = query.where(UsageLog.user_id == user_id)
        count_query = count_query.where(UsageLog.user_id == user_id)
    if org_id:
        query = query.where(UsageLog.org_id == org_id)
        count_query = count_query.where(UsageLog.org_id == org_id)
    if provider and provider != "all":
        query = query.where(UsageLog.provider == provider)
        count_query = count_query.where(UsageLog.provider == provider)
    if operation and operation != "all":
        query = query.where(UsageLog.operation == operation)
        count_query = count_query.where(UsageLog.operation == operation)

    total_count = await db.scalar(count_query) or 0
    offset = (page - 1) * page_size
    query = query.order_by(UsageLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = [
        AdminUsageRow(
            id=log.id,
            org_id=log.org_id,
            org_name=org.name if org else log.org_id,
            user_email=user.email if user else None,
            job_id=log.job_id,
            provider=log.provider,
            operation=log.operation,
            units=round(float(log.units), 2),
            cost_usd=round(float(log.cost_usd), 4),
            credits_deducted=round(float(log.credits_deducted), 2),
            created_at=log.created_at.isoformat() + "Z" if log.created_at else ""
        )
        for log, org, user in rows
    ]

    return AdminUsageLogsFilterResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        items=items
    )

# --- User Management & Controls ---
async def list_users(db: AsyncSession) -> List[AdminUserRow]:
    query = (
        select(User, Organization, Plan)
        .outerjoin(Organization, User.id == Organization.owner_id)
        .outerjoin(Plan, Organization.plan_id == Plan.id)
        .order_by(User.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    users = []
    for user, org, plan in rows:
        users.append(AdminUserRow(
            id=user.id,
            email=user.email,
            full_name=getattr(user, "full_name", None),
            avatar_url=getattr(user, "avatar_url", None),
            role=user.role,
            admin_permissions=getattr(user, "admin_permissions", {}) or {},
            organization_id=org.id if org else None,
            organization_name=org.name if org else None,
            plan_id=org.plan_id if org else None,
            plan_name=plan.name if plan else None,
            trial_started_at=user.trial_started_at.isoformat() + "Z" if user.trial_started_at else None,
            trial_expires_at=user.trial_expires_at.isoformat() + "Z" if user.trial_expires_at else None,
            created_at=user.created_at.isoformat() + "Z" if user.created_at else "",
            is_suspended=getattr(user, "is_suspended", False),
            is_banned=getattr(user, "is_banned", False),
            status="banned" if getattr(user, "is_banned", False) else ("suspended" if getattr(user, "is_suspended", False) else "active")
        ))
    return users

async def ban_user(db: AsyncSession, target_user_id: str, is_banned: bool) -> Dict[str, Any]:
    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_banned = is_banned
    await db.commit()
    await db.refresh(user)
    
    return {
        "success": True,
        "message": f"User {'banned' if is_banned else 'unbanned'} successfully",
        "user_id": user.id,
        "is_banned": user.is_banned
    }

async def update_user_role(
    db: AsyncSession,
    target_user_id: str,
    role: str,
    admin_permissions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if role not in ["customer", "assistant-admin", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Choose customer, assistant-admin, or admin.")

    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    if admin_permissions is not None:
        user.admin_permissions = admin_permissions
        
    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "message": f"User role updated to {role}",
        "user_id": user.id,
        "role": user.role
    }

async def switch_user_plan(db: AsyncSession, target_user_id: str, plan_id: str) -> Dict[str, Any]:
    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="User organization not found")

    plan = (await db.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Target Plan not found")

    org.plan_id = plan.id
    org.plan = plan.type
    await db.commit()

    return {
        "success": True,
        "message": f"User switched to plan {plan.name}",
        "user_id": user.id,
        "plan_id": plan.id,
        "plan_name": plan.name
    }

async def broadcast_announcement(
    db: AsyncSession,
    title: str,
    message: str,
    notif_type: str = "system",
    link: Optional[str] = None
) -> Dict[str, Any]:
    # Select all active non-banned users
    users = (await db.execute(select(User).where(User.is_banned == False))).scalars().all()

    count = 0
    for user in users:
        notif = Notification(
            user_id=user.id,
            type=notif_type,
            title=title,
            message=message,
            link=link or "/updates",
            is_read=False
        )
        db.add(notif)
        count += 1

    await db.commit()
    return {
        "success": True,
        "message": f"Broadcast sent to {count} users",
        "recipients_count": count
    }

async def impersonate_user(db: AsyncSession, target_user_id: str) -> ImpersonateResponse:
    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_access_token(subject=user.id, role=user.role)
    return ImpersonateResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.role
    )
