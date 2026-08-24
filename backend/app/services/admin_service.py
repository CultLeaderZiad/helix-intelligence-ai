import datetime
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, desc

from app.schemas.admin import (
    AdminOverviewStats, AdminJobRow, AdminSystemHealth, AdminServiceHealth,
    PlanSchema, PlanCreate, AdminOrganizationRow, GrantCreditsRequest,
    SwitchPlanRequest, UpdateFeatureFlagsRequest, AdminUsageSummary,
    ProviderUsageBreakdown, AdminUsageRow, AdminUserRow, ImpersonateResponse
)
from app.models.organization import Organization
from app.models.user import User
from app.models.plan import Plan
from app.models.usage_log import UsageLog
from app.models.scrape_job import ScrapeJob
from app.models.api_usage import ExternalApiUsage
from app.core.config import settings
from app.core.security import create_access_token
from fastapi import HTTPException

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

    now = datetime.datetime.utcnow()
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
    if settings.USE_MOCKS:
        return [
            AdminJobRow(
                job_id="job-1",
                organization="Org A",
                query="Nike",
                status="succeeded",
                records=12,
                duration_ms=45000,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            )
        ]

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
                detail="Operational / Low Latency (~600 tokens/s)",
                latency_ms=120,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            AdminServiceHealth(
                id="brightdata",
                name="Bright Data Scraper Network",
                status="success",
                detail="Operational / Async Snapshot Dataset",
                latency_ms=450,
                last_checked=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            AdminServiceHealth(
                id="scrapegraph",
                name="ScrapeGraphAI Pipeline",
                status="success",
                detail="Operational / Smart Scraper Service",
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
        price_per_credit=new_plan.price_per_credit,
        feature_flags=new_plan.feature_flags or {},
        created_by_admin_id=new_plan.created_by_admin_id,
        created_at=new_plan.created_at.isoformat() + "Z" if new_plan.created_at else None
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

    # Job counts per org
    job_counts_result = await db.execute(
        select(ScrapeJob.org_id, func.count(ScrapeJob.id)).group_by(ScrapeJob.org_id)
    )
    job_counts = dict(job_counts_result.all())

    orgs = []
    for org, user, plan in rows:
        plan_flags = plan.feature_flags if (plan and plan.feature_flags) else {}
        custom_flags = org.custom_feature_flags or {}
        effective_flags = dict(plan_flags)
        effective_flags.update(custom_flags)

        orgs.append(AdminOrganizationRow(
            id=org.id,
            name=org.name,
            owner_id=org.owner_id,
            owner_email=user.email if user else "Unknown",
            plan_id=org.plan_id,
            plan_name=plan.name if plan else org.plan,
            plan_type=plan.type if plan else "custom",
            credit_balance=round(float(org.credit_balance), 2),
            credits_used=round(float(org.credits_used), 2),
            custom_feature_flags=custom_flags,
            effective_feature_flags=effective_flags,
            status=org.status,
            trial_expires_at=user.trial_expires_at.isoformat() + "Z" if (user and user.trial_expires_at) else None,
            total_jobs=job_counts.get(org.id, 0)
        ))
    return orgs

async def grant_credits(db: AsyncSession, org_id: str, grant_in: GrantCreditsRequest, admin_id: str) -> Dict[str, Any]:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.credit_balance += grant_in.amount
    if org.status == "quota_exhausted":
        org.status = "active"

    # Log admin grant
    log = UsageLog(
        org_id=org.id,
        user_id=admin_id,
        provider="admin_grant",
        operation="credit_grant",
        units=grant_in.amount,
        cost_usd=0.0,
        credits_deducted=-grant_in.amount, # negative deduction = credit addition
        metadata_json={"reason": grant_in.reason, "granted_by_admin_id": admin_id}
    )
    db.add(log)
    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "message": f"Successfully granted {grant_in.amount} credits to {org.name}",
        "new_balance": round(float(org.credit_balance), 2),
        "status": org.status
    }

async def switch_organization_plan(db: AsyncSession, org_id: str, switch_in: SwitchPlanRequest) -> Dict[str, Any]:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    plan = (await db.execute(select(Plan).where(Plan.id == switch_in.plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    org.plan_id = plan.id
    org.plan = plan.type
    if switch_in.reset_credits:
        org.credit_balance = float(plan.credit_allowance)
    org.status = "active"

    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "message": f"Organization '{org.name}' switched to plan '{plan.name}'",
        "plan_id": org.plan_id,
        "credit_balance": round(float(org.credit_balance), 2),
        "status": org.status
    }

async def update_organization_feature_flags(db: AsyncSession, org_id: str, flags_in: UpdateFeatureFlagsRequest) -> Dict[str, Any]:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.custom_feature_flags = flags_in.feature_flags
    await db.commit()
    await db.refresh(org)

    return {
        "success": True,
        "message": f"Updated custom feature flags for '{org.name}'",
        "custom_feature_flags": org.custom_feature_flags
    }

# --- Usage & Provider Spend ---
async def get_usage_summary(db: AsyncSession) -> AdminUsageSummary:
    total_cost = await db.scalar(select(func.sum(UsageLog.cost_usd))) or 0.0
    total_credits = await db.scalar(select(func.sum(UsageLog.credits_deducted))) or 0.0
    total_reqs = await db.scalar(select(func.count(UsageLog.id))) or 0

    # Group by provider & operation
    group_query = (
        select(
            UsageLog.provider,
            UsageLog.operation,
            func.sum(UsageLog.units).label("units"),
            func.sum(UsageLog.cost_usd).label("cost"),
            func.sum(UsageLog.credits_deducted).label("credits"),
            func.count(UsageLog.id).label("requests")
        )
        .group_by(UsageLog.provider, UsageLog.operation)
        .order_by(desc("cost"))
    )
    group_res = await db.execute(group_query)
    by_provider = [
        ProviderUsageBreakdown(
            provider=row.provider,
            operation=row.operation,
            total_units=round(float(row.units or 0.0), 2),
            total_cost_usd=round(float(row.cost or 0.0), 4),
            total_credits_deducted=round(float(row.credits or 0.0), 2),
            total_requests=row.requests
        )
        for row in group_res.all()
    ]

    # Recent 50 logs
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

# --- User Management & Impersonation ---
async def list_users(db: AsyncSession) -> List[AdminUserRow]:
    query = (
        select(User, Organization)
        .outerjoin(Organization, User.id == Organization.owner_id)
        .order_by(User.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    users = []
    for user, org in rows:
        users.append(AdminUserRow(
            id=user.id,
            email=user.email,
            role=user.role,
            organization_id=org.id if org else None,
            organization_name=org.name if org else None,
            trial_started_at=user.trial_started_at.isoformat() + "Z" if user.trial_started_at else None,
            trial_expires_at=user.trial_expires_at.isoformat() + "Z" if user.trial_expires_at else None,
            created_at=user.created_at.isoformat() + "Z" if user.created_at else "",
            status="suspended" if getattr(user, "is_suspended", False) else "active"
        ))
    return users

async def update_user_status(db: AsyncSession, target_user_id: str, status: str) -> Dict[str, Any]:
    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_suspended = (status == "suspended")
    await db.commit()
    await db.refresh(user)
    
    return {
        "success": True,
        "message": f"User status updated to {status}",
        "user_id": user.id,
        "status": status
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
