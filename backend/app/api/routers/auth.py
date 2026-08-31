from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime

from app.db.session import async_session_maker
from app.schemas.auth import UserCreate, UserLogin, SessionResponse
from app.services import auth_service, billing_service
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan

router = APIRouter()

async def build_session_response(db: AsyncSession, user: User, access_token: str = None) -> SessionResponse:
    org = await billing_service.get_or_create_default_org(db, user)
    plan = None
    if org.plan_id:
        plan = (await db.execute(select(Plan).where(Plan.id == org.plan_id))).scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()

    effective_flags = dict(plan.feature_flags or {}) if plan else {}
    if org.custom_feature_flags:
        effective_flags.update(org.custom_feature_flags)

    now = datetime.datetime.now(datetime.timezone.utc)
    trial_days_remaining = None
    if user.trial_expires_at:
        trial_exp = user.trial_expires_at
        if trial_exp.tzinfo is None:
            trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
        trial_days_remaining = max(0, (trial_exp - now).days) if trial_exp > now else 0

    # Daily usage info
    from app.services.billing_service import _ensure_daily_reset, _utc_midnight, get_trial_usage_summary
    await _ensure_daily_reset(db, org)
    daily_limit = getattr(plan, "daily_credit_limit", None) if plan else None
    daily_used = round(float(org.daily_credits_used_today or 0.0), 2)
    daily_remaining = round(max(0.0, (daily_limit or 0.0) - daily_used), 2) if daily_limit is not None else None
    daily_resets_at = None
    if daily_limit:
        daily_resets_at = (_utc_midnight(now) + datetime.timedelta(days=1)).isoformat()

    trial_summary = await get_trial_usage_summary(db, user, org)

    # Administrator Full Privilege Override
    credit_balance = round(float(org.credit_balance or 0.0), 2)
    if user.role == "admin":
        effective_flags = {
            "discover": True,
            "intelligence": True,
            "create": True,
            "performance": True,
            "swipe_files": True,
            "team_accounts": True,
            "public_api": True,
            "ai_insights": True,
            "create_media": True,
            "advanced_scoring": True,
            "bulk_export": True,
            "custom_webhooks": True,
        }
        trial_days_remaining = None
        daily_limit = None
        daily_remaining = 999999.0
        credit_balance = max(credit_balance, 999999.0)

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        feature_flags=effective_flags,
        credit_balance=credit_balance,
        trial_days_remaining=trial_days_remaining,
        daily_credit_limit=daily_limit,
        daily_credits_used=daily_used,
        daily_credits_remaining=daily_remaining,
        daily_credits_resets_at_utc=daily_resets_at,
        trial_active=trial_summary.get("trial_active", True),
        images_used_today=trial_summary.get("images_used_today", 0),
        images_daily_limit=trial_summary.get("images_daily_limit", 5),
        images_remaining_today=trial_summary.get("images_remaining_today", 5),
        images_trial_total=trial_summary.get("images_trial_total", 0),
        trial_ends_at=trial_summary.get("trial_ends_at"),
        requires_plan=trial_summary.get("requires_plan", False),
        plan_id=org.plan_id or "plan_trial_default",
        has_completed_onboarding=getattr(user, "has_completed_onboarding", False)
    )

@router.post("/sign-up", response_model=SessionResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    try:
        user = await auth_service.register_user(db, user_in)
        from app.core.security import create_access_token
        token = create_access_token(subject=user.id, role=user.role)
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Sign-up failed for {user_in.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign-up error: {type(e).__name__}: {e}"
        )

@router.post("/sign-in", response_model=SessionResponse)
async def signin(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    try:
        token = await auth_service.authenticate_user(db, user_in)
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(UserModel.email == user_in.email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User found during auth but not on second query")
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Sign-in failed for {user_in.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during sign-in: {type(e).__name__}: {e}")

@router.post("/sign-out")
async def signout():
    return {"message": "Successfully signed out"}

@router.get("/session", response_model=SessionResponse)
async def get_session(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await build_session_response(db, current_user)

@router.post("/session/onboarding/complete")
async def complete_onboarding(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.has_completed_onboarding = True
    await db.commit()
    return {"message": "Onboarding marked as complete"}

from fastapi import Request
import hmac
import hashlib
from app.core.config import settings

@router.post("/webhook")
async def neon_auth_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    
    signature = request.headers.get("better-auth-signature")
    if settings.NEON_WEBHOOK_SECRET and signature:
        expected_signature = hmac.new(
            settings.NEON_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        import logging
        logging.info(f"Webhook signature check. Received: {signature}, Expected: {expected_signature}")

    try:
        import json
        payload = json.loads(body.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    data = payload.get("data", {})
    user_data = data.get("user", {})
    
    if event == "user.created" and user_data:
        user_id = user_data.get("id")
        email = user_data.get("email")
        name = user_data.get("name", "")
        
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Missing user_id or email")
            
        result = await db.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            now = datetime.datetime.now(datetime.timezone.utc)
            trial_expires = now + datetime.timedelta(days=14)

            new_user = User(
                id=user_id,
                email=email,
                password_hash="EXTERNAL_AUTH_MANAGED",
                role="customer",
                trial_started_at=now,
                trial_expires_at=trial_expires
            )
            db.add(new_user)
            await db.commit()
            
            await billing_service.get_or_create_default_org(db, new_user)
            
            return {"message": "User synchronized successfully"}
            
    return {"message": "Webhook received"}
