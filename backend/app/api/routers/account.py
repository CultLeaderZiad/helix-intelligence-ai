import datetime
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.schemas.account import TrialStatusResponse
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.usage_log import UsageLog
from app.services.ai.ai_router import TRIAL_DAILY_REQUEST_LIMIT
from app.services import billing_service, api_key_service, team_service

router = APIRouter()

class CreateApiKeyRequest(BaseModel):
    name: str = "Default API Key"

class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"

class AcceptInviteRequest(BaseModel):
    token: str

@router.get("/trial-status", response_model=TrialStatusResponse)
async def get_trial_status(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    now = datetime.datetime.now(datetime.timezone.utc)
    
    is_active = False
    days_remaining = 0
    
    if current_user.trial_expires_at:
        if now < current_user.trial_expires_at:
            is_active = True
            delta = current_user.trial_expires_at - now
            days_remaining = max(0, delta.days)

    # Get today's request count
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(func.count(UsageLog.id)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start
    )
    usage_count = await db.scalar(query) or 0

    # Get daily credit usage from org
    from app.services.billing_service import get_or_create_default_org, _ensure_daily_reset, _utc_midnight
    org = await get_or_create_default_org(db, current_user)
    from app.models.plan import Plan
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one()

    daily_limit = getattr(plan, "daily_credit_limit", None)
    daily_used = round(float(org.daily_credits_used_today), 2)
    daily_remaining = round(max(0, (daily_limit or 0) - daily_used), 2) if daily_limit else None
    daily_resets_at = None
    if daily_limit:
        daily_resets_at = (_utc_midnight(now) + datetime.timedelta(days=1)).isoformat()
    
    return TrialStatusResponse(
        active=is_active,
        days_remaining=days_remaining,
        requests_used=usage_count,
        requests_limit=TRIAL_DAILY_REQUEST_LIMIT,
        daily_credit_limit=daily_limit,
        daily_credits_used=daily_used,
        daily_credits_remaining=daily_remaining,
        daily_credits_resets_at_utc=daily_resets_at
    )

@router.post("/onboarding-complete")
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.has_completed_onboarding = True
    await db.commit()
    return {"status": "ok"}

@router.get("/billing")
async def get_billing(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await billing_service.get_org_billing_summary(db, current_user)

# --- Public API Keys (Gated by 'public_api') ---
@router.get("/api-keys")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await api_key_service.list_api_keys(db, current_user)

@router.post("/api-keys")
async def create_api_key(
    req: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await api_key_service.generate_api_key(db, current_user, req.name)

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await api_key_service.revoke_api_key(db, current_user, key_id)

# --- Team Multi-Seat (Gated by 'team_accounts') ---
@router.get("/team")
async def get_team(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await team_service.list_team(db, current_user)

@router.post("/team/invites")
async def invite_team_member(
    req: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await team_service.invite_member(db, current_user, req.email, req.role)

@router.delete("/team/invites/{invite_id}")
async def cancel_team_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await team_service.cancel_invite(db, current_user, invite_id)

@router.post("/team/invites/accept")
async def accept_team_invite(
    req: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await team_service.accept_invite(db, req.token, current_user)
