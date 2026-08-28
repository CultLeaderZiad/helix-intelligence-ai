from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.schemas.admin import (
    AdminOverviewStats, AdminJobRow, AdminSystemHealth,
    PlanSchema, PlanCreate, AdminOrganizationRow, GrantCreditsRequest,
    SwitchPlanRequest, UpdateFeatureFlagsRequest, AdminUsageSummary,
    AdminUserRow, ImpersonateResponse, UserStatusUpdate
)
from app.services import admin_service
from app.core.deps import get_db, get_current_admin
from app.models.user import User

router = APIRouter()

# --- System & Overview ---
@router.get("/overview/stats", response_model=AdminOverviewStats)
async def get_overview(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_overview(db)

@router.get("/jobs", response_model=List[AdminJobRow])
async def list_jobs(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_jobs(db)

@router.get("/system/health", response_model=AdminSystemHealth)
async def get_health(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_health(db)

# --- Plans Management ---
@router.get("/plans", response_model=List[PlanSchema])
async def list_plans(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_plans(db)

@router.post("/plans", response_model=PlanSchema)
async def create_plan(plan_in: PlanCreate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.create_plan(db, plan_in, current_admin.id)

# --- Organizations & Quota Controls ---
@router.get("/organizations", response_model=List[AdminOrganizationRow])
async def list_organizations(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_organizations(db)

@router.post("/organizations/{org_id}/grant-credits")
async def grant_credits(
    org_id: str,
    grant_in: GrantCreditsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.grant_credits(db, org_id, grant_in, current_admin.id)

@router.post("/organizations/{org_id}/switch-plan")
async def switch_plan(
    org_id: str,
    switch_in: SwitchPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.switch_organization_plan(db, org_id, switch_in)

@router.post("/organizations/{org_id}/feature-flags")
async def update_feature_flags(
    org_id: str,
    flags_in: UpdateFeatureFlagsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.update_organization_feature_flags(db, org_id, flags_in)

# --- Usage & Provider Cost Breakdown ---
@router.get("/usage", response_model=AdminUsageSummary)
async def get_usage_summary(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_usage_summary(db)

# --- User Management & Impersonation ---
@router.get("/users", response_model=List[AdminUserRow])
async def list_users(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_users(db)

@router.post("/users/{user_id}/status", response_model=Dict[str, Any])
async def update_user_status(
    user_id: str,
    status_in: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.update_user_status(db, user_id, status_in.status)

@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.impersonate_user(db, user_id)
