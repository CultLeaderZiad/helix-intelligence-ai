from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.schemas.admin import (
    AdminOverviewStats, AdminJobRow, AdminSystemHealth,
    PlanSchema, PlanCreate, PlanUpdate, AdminOrganizationRow, GrantCreditsRequest,
    SwitchPlanRequest, UpdateFeatureFlagsRequest, AdminUsageSummary,
    AdminUserRow, ImpersonateResponse, UserStatusUpdate, UserBanRequest,
    UserRoleRequest, UserPlanSwitchRequest, AdminBroadcastRequest,
    AdminUsageLogsFilterResponse
)
from app.services import admin_service, support_service
from app.core.deps import get_db, get_current_admin, get_current_full_admin
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
async def create_plan(
    plan_in: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.create_plan(db, plan_in, current_admin.id)

@router.put("/plans/{plan_id}", response_model=PlanSchema)
async def update_plan(
    plan_id: str,
    plan_in: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.update_plan(db, plan_id, plan_in)

# --- Organizations & Quota Controls ---
@router.get("/organizations", response_model=List[AdminOrganizationRow])
async def list_organizations(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_organizations(db)

@router.post("/organizations/{org_id}/grant-credits")
async def grant_credits(
    org_id: str,
    grant_in: GrantCreditsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.grant_credits(db, org_id, grant_in, current_admin.id)

@router.post("/organizations/{org_id}/switch-plan")
async def switch_plan(
    org_id: str,
    switch_in: SwitchPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.switch_organization_plan(db, org_id, switch_in)

@router.post("/organizations/{org_id}/feature-flags")
async def update_feature_flags(
    org_id: str,
    flags_in: UpdateFeatureFlagsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.update_organization_feature_flags(db, org_id, flags_in)

# --- Usage & Provider Cost Breakdown ---
@router.get("/usage", response_model=AdminUsageSummary)
async def get_usage_summary(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_usage_summary(db)

@router.get("/usage/logs", response_model=AdminUsageLogsFilterResponse)
async def get_usage_logs_filtered(
    user_id: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.get_usage_logs_filtered(
        db=db,
        user_id=user_id,
        org_id=org_id,
        provider=provider,
        operation=operation,
        page=page,
        page_size=page_size
    )

# --- User Management & Impersonation ---
@router.get("/users", response_model=List[AdminUserRow])
async def list_users(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_users(db)

@router.post("/users/{user_id}/status", response_model=Dict[str, Any])
async def update_user_status(
    user_id: str,
    status_in: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.update_user_status(db, user_id, status_in.status)

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    ban_in: UserBanRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.ban_user(db, user_id, ban_in.is_banned)

@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_in: UserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.update_user_role(db, user_id, role_in.role, role_in.admin_permissions)

@router.post("/users/{user_id}/plan")
async def switch_user_plan(
    user_id: str,
    plan_in: UserPlanSwitchRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.switch_user_plan(db, user_id, plan_in.plan_id)

@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await admin_service.impersonate_user(db, user_id)

# --- Admin Broadcast Announcements ---
@router.post("/broadcast")
async def broadcast_announcement(
    broadcast_in: AdminBroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_full_admin)
):
    return await admin_service.broadcast_announcement(
        db=db,
        title=broadcast_in.title,
        message=broadcast_in.message,
        notif_type=broadcast_in.type,
        link=broadcast_in.link
    )

# --- Admin Support Tickets Hub ---
@router.get("/support/tickets")
async def list_admin_tickets(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await support_service.list_admin_tickets(db, status_filter=status, type_filter=type)

class TicketReplyBody(BaseModel):
    message: str

@router.post("/support/tickets/{ticket_id}/reply")
async def reply_admin_ticket(
    ticket_id: str,
    body: TicketReplyBody,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await support_service.add_reply(db, ticket_id, current_admin, body.message)

class TicketStatusBody(BaseModel):
    status: str

@router.patch("/support/tickets/{ticket_id}/status")
async def update_admin_ticket_status(
    ticket_id: str,
    body: TicketStatusBody,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await support_service.update_ticket_status(db, ticket_id, body.status)
