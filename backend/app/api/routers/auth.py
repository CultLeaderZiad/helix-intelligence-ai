import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime

from app.core.observability import log_event
from app.schemas.auth import UserCreate, UserLogin, SessionResponse, PasswordResetRequest, PasswordResetConfirm
from app.services import auth_service, billing_service
from app.core.deps import _bind_request_tenant, get_db, get_current_user, oauth2_scheme
from app.models.user import User
from app.models.plan import Plan
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

async def build_session_response(db: AsyncSession, user: User, access_token: str = None) -> SessionResponse:
    org = None
    try:
        org = await billing_service.get_or_create_default_org(db, user)
    except Exception as org_err:
        log_event(logger, "session_org_lookup_failed", error=org_err, actor_id=user.id)

    plan = None
    if org and org.plan_id:
        try:
            plan = (await db.execute(select(Plan).where(Plan.id == org.plan_id))).scalar_one_or_none()
        except Exception as exc:
            log_event(logger, "session_plan_lookup_failed", error=exc, actor_id=user.id, tenant_id=org.id)
    if not plan:
        try:
            plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
        except Exception as exc:
            log_event(logger, "session_default_plan_lookup_failed", error=exc, actor_id=user.id)

    effective_flags = dict(plan.feature_flags or {}) if plan and plan.feature_flags else {}
    if org and org.custom_feature_flags:
        effective_flags.update(org.custom_feature_flags)
    # SECURITY: custom_feature_flags also holds workspace credentials
    # (hunter_api_key, linkedin_cookie). Never echo those to the client, and
    # never let them into a Dict[str, bool] response contract.
    _CREDENTIAL_MARKERS = ("api_key", "apikey", "cookie", "secret", "token", "password")
    effective_flags = {
        k: v
        for k, v in effective_flags.items()
        if not any(marker in str(k).lower() for marker in _CREDENTIAL_MARKERS)
    }

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
        log_event(logger, "session_daily_reset_failed", error=reset_err, actor_id=user.id, tenant_id=getattr(org, "id", None))

    trial_summary = {}
    try:
        if org:
            from app.services.billing_service import get_trial_usage_summary
            trial_summary = await get_trial_usage_summary(db, user, org)
    except Exception as trial_err:
        log_event(logger, "session_trial_summary_failed", error=trial_err, actor_id=user.id, tenant_id=getattr(org, "id", None))

    # Administrator Full Privilege Override
    credit_balance = round(float(getattr(org, "credit_balance", 25.0) or 0.0), 2) if org else 25.0
    platform_admin = billing_service.is_platform_admin(user)
    if platform_admin:
        effective_flags = {
            "discover": True,
            "intelligence": True,
            "create": True,
            "performance": True,
            "swipe_files": True,
            "team_accounts": True,
            "public_api": True,
            "scout": True,
            "leadgen": True,
            "monitors": True,
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

    access_status = "approved" if platform_admin else "pending"
    if org and access_status != "approved":
        try:
            access_status = (await billing_service.access_status_for_org(db, org.id))["status"]
        except Exception as access_err:
            log_event(logger, "session_access_status_failed", error=access_err, actor_id=user.id, tenant_id=org.id)
            access_status = "pending"
    if access_status != "approved":
        effective_flags = {key: False for key in effective_flags}

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
        org_id=org.id if org else None,
        org_name=org.name if org else None,
        access_status=access_status,
        is_platform_admin=platform_admin,
        has_completed_onboarding=getattr(user, "has_completed_onboarding", False)
    )

@router.post("/sign-up", response_model=SessionResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register_user(db, user_in)
        from app.core.security import create_access_token
        token_ver = (user.signup_metadata or {}).get("token_version", 1)
        token = create_access_token(subject=user.id, role=user.role, token_version=token_ver)
        # Fire-and-forget welcome email — completely decoupled from SQLAlchemy session
        try:
            import asyncio
            from app.services import lifecycle_email_service
            asyncio.create_task(lifecycle_email_service.send_welcome_email(user.email, user.full_name or ""))
        except Exception as mail_err:
            log_event(logger, "welcome_email_scheduling_failed", error=mail_err, actor_id=user.id)
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        log_event(logger, "signup_failed", error=e)
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
    try:
        token = await auth_service.authenticate_user(db, user_in)
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(func.lower(UserModel.email) == user_in.email.lower().strip()))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        await _bind_request_tenant(db, user)
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        log_event(logger, "signin_failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign-in temporarily unavailable. Please try again shortly.",
        )

@router.post("/sign-out")
@router.post("/logout")
async def signout(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
):
    """Revoke active user sessions and sign out."""
    actor_id = None
    if token:
        try:
            from app.core.security import verify_neon_token
            payload = await verify_neon_token(token)
            if payload and payload.get("sub"):
                actor_id = payload["sub"]
                res = await db.execute(select(User).where(User.id == payload["sub"]))
                user = res.scalar_one_or_none()
                if user:
                    await auth_service.revoke_user_sessions(db, user)
                    log_event(logger, "sessions_revoked", actor_id=user.id, level=logging.INFO)
        except Exception as exc:
            log_event(logger, "session_revocation_failed", error=exc, actor_id=actor_id)
            raise HTTPException(status_code=503, detail={
                "code": "session_revocation_unavailable",
                "message": "Server-side sign-out could not be confirmed. Please retry.",
            }) from None
    return {"message": "Successfully signed out"}

@router.post("/forgot-password")
async def forgot_password(req: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Start a password reset. The public response is identical whether or
    not the account exists (no account enumeration). The reset link is sent via
    transactional email when email is configured, and never logged in plain text."""
    try:
        user_and_token = await auth_service.request_password_reset(db, req.email)
    except HTTPException:
        raise
    except Exception as e:
        log_event(logger, "password_reset_request_failed", error=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset request failed")

    if user_and_token:
        user, raw_token = user_and_token
        reset_url = f"{settings.PUBLIC_APP_BASE_URL}/reset-password?token={raw_token}"
        # F17: Never log plain reset token or URL
        log_event(logger, "password_reset_requested", actor_id=user.id, level=logging.INFO)
        
        from app.services.email_service import send_email, email_enabled
        if email_enabled():
            subject = "Reset your Helix Intelligence password"
            html_body = f"""
            <div style="font-family:Inter,Arial,sans-serif;background:#0A0A0A;color:#EDEDED;padding:32px;">
              <div style="max-width:560px;margin:0 auto;background:#111;border:1px solid #222;border-radius:12px;padding:32px;">
                <div style="font-size:13px;letter-spacing:2px;color:#6366F1;font-weight:700;margin-bottom:16px;">HELIX INTELLIGENCE</div>
                <h1 style="font-size:22px;margin:0 0 16px;color:#fff;">Password Reset Request</h1>
                <p style="font-size:15px;line-height:1.6;color:#B5B5B5;">We received a request to reset your password. Click the button below to set a new password. This link is valid for {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
                <a href="{reset_url}" style="display:inline-block;margin-top:24px;background:#6366F1;color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;">Reset Password</a>
                <p style="margin-top:28px;font-size:12px;color:#666;">If you did not request this, you can safely ignore this email.</p>
              </div>
            </div>
            """
            try:
                await send_email(to=user.email, subject=subject, html=html_body)
            except Exception as mail_err:
                log_event(logger, "password_reset_delivery_failed", error=mail_err, actor_id=user.id)

        return {"ok": True}
    return {"ok": True}

@router.post("/reset-password")
async def reset_password(req: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Redeem a reset token and set a new password. Returns a fresh session
    so the frontend can move straight into the app."""
    try:
        user = await auth_service.reset_password(db, req.token, req.new_password)
    except HTTPException:
        raise
    except Exception as e:
        log_event(logger, "password_reset_failed", error=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset failed")

    log_event(logger, "password_reset_completed", actor_id=user.id, level=logging.INFO)
    await _bind_request_tenant(db, user)
    from app.core.security import create_access_token
    token_ver = (user.signup_metadata or {}).get("token_version", 1)
    token = create_access_token(subject=user.id, role=user.role, token_version=token_ver)
    return await build_session_response(db, user, access_token=token)

@router.get("/session", response_model=SessionResponse)
async def get_session(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await build_session_response(db, current_user)

@router.post("/session/onboarding/complete")
async def complete_onboarding(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.has_completed_onboarding = True
    await db.commit()
    log_event(logger, "onboarding_completed", actor_id=current_user.id, level=logging.INFO)
    return {"message": "Onboarding marked as complete"}

@router.post("/session/onboarding/restart")
async def restart_onboarding(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.has_completed_onboarding = False
    await db.commit()
    log_event(logger, "onboarding_restarted", actor_id=current_user.id, level=logging.INFO)
    return {"message": "Onboarding marked as incomplete"}

from fastapi import Request
import hmac

@router.post("/webhook")
async def neon_auth_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()

    # SECURITY: this endpoint creates users and organizations, so the caller MUST
    # be authenticated. Fail CLOSED: Neon Auth URL missing -> refuse (503);
    # missing/invalid signature -> 401.
    if not (settings.NEON_AUTH_URL or "").strip():
        raise HTTPException(status_code=503, detail="Auth webhook is not configured")

    from app.services.neon_webhook import process_auth_webhook, verify_and_parse

    try:
        payload = await verify_and_parse(body, request.headers)
    except HTTPException:
        raise
    header_event_id = (request.headers.get("x-neon-event-id") or "").strip()
    body_event_id = str(payload.get("event_id") or "")
    if not header_event_id or not body_event_id or not hmac.compare_digest(header_event_id, body_event_id):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        return await process_auth_webhook(db, payload)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        log_event(logger, "auth_webhook_processing_failed", error=exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")
