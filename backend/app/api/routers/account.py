import os
import uuid
import datetime
from fastapi import APIRouter, Depends, Body, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.schemas.account import TrialStatusResponse
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.usage_log import UsageLog
from app.models.organization import Organization
from app.services.ai.ai_router import TRIAL_DAILY_REQUEST_LIMIT
from app.services import billing_service, api_key_service, team_service, storage_service
from app.core.security import get_password_hash, verify_password

router = APIRouter()

class CreateApiKeyRequest(BaseModel):
    name: str = "Default API Key"

class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"

class AcceptInviteRequest(BaseModel):
    token: str

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": getattr(current_user, "full_name", "") or "",
        "avatar_url": getattr(current_user, "avatar_url", "") or "",
        "role": current_user.role,
        "has_completed_onboarding": getattr(current_user, "has_completed_onboarding", False),
        "trial_expires_at": current_user.trial_expires_at.isoformat() if current_user.trial_expires_at else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else ""
    }

@router.patch("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url
    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password")
        if not await verify_password(req.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password does not match")
        current_user.password_hash = get_password_hash(req.new_password)

    await db.commit()
    await db.refresh(current_user)
    return {
        "status": "ok",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role
        }
    }

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contents = await file.read()
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    filename = f"avatar_{current_user.id}_{int(datetime.datetime.utcnow().timestamp())}.{ext}"
    
    avatar_url = await storage_service.save_file(contents, filename)
    current_user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return {"status": "ok", "avatar_url": avatar_url}

@router.get("/usage/today")
async def get_today_real_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Total credits deducted today
    credits_stmt = select(func.sum(UsageLog.credits_deducted)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start
    )
    credits_deducted_today = round(float((await db.scalar(credits_stmt)) or 0.0), 2)

    # 2. Total searches run today
    searches_stmt = select(func.count(UsageLog.id)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start,
        UsageLog.operation.ilike("%search%")
    )
    searches_today = await db.scalar(searches_stmt) or 0

    # 3. Total images/media generated today
    media_stmt = select(func.count(UsageLog.id)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start,
        UsageLog.operation.ilike("%generate%")
    )
    media_today = await db.scalar(media_stmt) or 0

    # 4. Org limits
    org = await billing_service.get_or_create_default_org(db, current_user)
    from app.models.plan import Plan
    plan_res = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_res.scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()

    daily_credit_limit = getattr(plan, "daily_credit_limit", None) if plan else None
    daily_image_limit = getattr(plan, "daily_image_limit", 5) if plan else 5
    daily_video_limit = getattr(plan, "daily_video_limit", 3) if plan else 3

    return {
        "credits_consumed_today": credits_deducted_today,
        "searches_run_today": searches_today,
        "images_generated_today": media_today,
        "daily_credit_limit": daily_credit_limit,
        "daily_image_limit": daily_image_limit,
        "daily_video_limit": daily_video_limit,
        "credit_balance": round(float(org.credit_balance or 0.0), 2),
        "as_of_utc": now.isoformat()
    }

@router.get("/trial-status", response_model=TrialStatusResponse)
async def get_trial_status(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    now = datetime.datetime.now(datetime.timezone.utc)
    
    is_active = False
    days_remaining = 0
    
    if getattr(current_user, "role", "") == "admin":
        is_active = True
        days_remaining = 999
    elif current_user.trial_expires_at:
        if now < current_user.trial_expires_at:
            is_active = True
            delta = current_user.trial_expires_at - now
            days_remaining = max(0, delta.days)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(func.count(UsageLog.id)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start
    )
    usage_count = await db.scalar(query) or 0

    from app.services.billing_service import get_or_create_default_org, _ensure_daily_reset, _utc_midnight
    org = await get_or_create_default_org(db, current_user)
    from app.models.plan import Plan
    plan_result = await db.execute(select(Plan).where(Plan.id == org.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()

    daily_limit = getattr(plan, "daily_credit_limit", None) if plan else None
    daily_used = round(float(org.daily_credits_used_today or 0.0), 2)
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
