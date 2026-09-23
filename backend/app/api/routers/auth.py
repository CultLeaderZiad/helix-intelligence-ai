from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime

from app.db.session import async_session_maker
from app.schemas.auth import UserCreate, UserLogin, SessionResponse, PasswordResetRequest, PasswordResetConfirm
from app.services import auth_service, billing_service
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.core.config import settings

router = APIRouter()

async def build_session_response(db: AsyncSession, user: User, access_token: str = None) -> SessionResponse:
    import logging
    logger = logging.getLogger(__name__)

    org = None
    try:
        org = await billing_service.get_or_create_default_org(db, user)
    except Exception as org_err:
        logger.warning(f"Default org retrieval failed for user {user.id}: {org_err}")

    plan = None
    if org and org.plan_id:
        try:
            plan = (await db.execute(select(Plan).where(Plan.id == org.plan_id))).scalar_one_or_none()
        except Exception:
            pass
    if not plan:
        try:
            plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
        except Exception:
            pass

    effective_flags = dict(plan.feature_flags or {}) if plan and plan.feature_flags else {}
    if org and org.custom_feature_flags:
        effective_flags.update(org.custom_feature_flags)

    now = datetime.datetime.now(datetime.timezone.utc)
    trial_days_remaining = None
    if user.trial_expires_at:
        trial_exp = user.trial_expires_at
        if trial_exp.tzinfo is None:
            trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
        trial_days_remaining = max(0, (trial_exp - now).days) if trial_exp > now else 0

    daily_limit = getattr(plan, "daily_credit_limit", None) if plan else None
    daily_used = round(float(getattr(org, "daily_credits_used_today", 0.0) or 0.0), 2) if org else 0.0
    daily_remaining = round(max(0.0, (daily_limit or 0.0) - daily_used), 2) if daily_limit is not None else None
    daily_resets_at = None

    try:
        if org:
            from app.services.billing_service import _ensure_daily_reset, _utc_midnight
            await _ensure_daily_reset(db, org)
            if daily_limit:
                daily_resets_at = (_utc_midnight(now) + datetime.timedelta(days=1)).isoformat()
    except Exception as reset_err:
        logger.warning(f"Daily reset check error for user {user.id}: {reset_err}")

    trial_summary = {}
    try:
        if org:
            from app.services.billing_service import get_trial_usage_summary
            trial_summary = await get_trial_usage_summary(db, user, org)
    except Exception as trial_err:
        logger.warning(f"Trial usage summary error for user {user.id}: {trial_err}")

    # Administrator Full Privilege Override
    credit_balance = round(float(getattr(org, "credit_balance", 25.0) or 0.0), 2) if org else 25.0
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

    display_name = getattr(user, "full_name", None) or (user.email.split("@")[0] if user.email else "user")

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        name=display_name,
        full_name=getattr(user, "full_name", None),
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
        plan_id=(org.plan_id if org else None) or "plan_trial_default",
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
        # Fire-and-forget welcome email — completely decoupled from SQLAlchemy session
        try:
            import asyncio
            from app.services import lifecycle_email_service
            asyncio.create_task(lifecycle_email_service.send_welcome_email(user.email, user.full_name or ""))
        except Exception as mail_err:
            logger.warning(f"Welcome email scheduling failed for {user.email}: {mail_err}")
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Sign-up failed for {user_in.email}: {e}")
        err_msg = str(e).lower()
        if "unique" in err_msg or "integrity" in err_msg or "already exists" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account registration is temporarily unavailable. Please try again in a few moments."
        )

@router.post("/sign-in", response_model=SessionResponse)
async def signin(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    try:
        token = await auth_service.authenticate_user(db, user_in)
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(func.lower(UserModel.email) == user_in.email.lower().strip()))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Sign-in failed for {user_in.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign-in temporarily unavailable. Please try again shortly.",
        )

@router.post("/sign-out")

async def signout():
    return {"message": "Successfully signed out"}

@router.post("/forgot-password")
async def forgot_password(req: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Start a password reset. The public response is identical whether or
    not the account exists (no account enumeration). The reset link is still
    logged server-side; when AUTH_DEV_RESET_RETURN is enabled it is also
    returned in the response because no mail provider is bundled."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        user_and_token = await auth_service.request_password_reset(db, req.email)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Password reset request failed for {req.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset request failed")

    if user_and_token:
        user, raw_token = user_and_token
        reset_url = f"{settings.PUBLIC_APP_BASE_URL}/reset-password?token={raw_token}"
        logger.warning(
            "PASSWORD RESET link issued for %s: %s (dev delivery — no mail provider configured)",
            user.email, reset_url,
        )
        if getattr(settings, "AUTH_DEV_RESET_RETURN", False):
            return {"ok": True, "reset_url": reset_url, "expires_in_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES}
        return {"ok": True}
    return {"ok": True}

@router.post("/reset-password")
async def reset_password(req: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Redeem a reset token and set a new password. Returns a fresh session
    so the frontend can move straight into the app."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        user = await auth_service.reset_password(db, req.token, req.new_password)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Password reset failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset failed")

    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, role=user.role)
    return await build_session_response(db, user, access_token=token)

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
