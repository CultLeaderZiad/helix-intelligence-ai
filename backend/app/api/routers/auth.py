import datetime
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.rate_limit import client_ip, throttle

from app.db.session import async_session_maker
from app.schemas.auth import UserCreate, UserLogin, SessionResponse, PasswordResetRequest, PasswordResetConfirm
from app.services import auth_service, billing_service
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.core.config import settings
from app.core.security import verify_inbound_webhook_signature

router = APIRouter()
logger = logging.getLogger(__name__)

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
    try:
        user = await auth_service.register_user(db, user_in)
        from app.core.security import create_access_token
        token = create_access_token(subject=user.id, role=user.role)
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        # Same rule as sign-in: the exception text stays in the server log.
        # "Email already registered" style conflicts come from the service as
        # HTTPException and are unaffected by this branch.
        logger.exception("Sign-up failed for %s: %s", user_in.email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Sign-up could not be completed. Try again."},
        )

@router.post("/sign-in", response_model=SessionResponse)
async def signin(user_in: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange credentials for a session.

    Failure text is deliberately generic on the wire: `authenticate_user`
    raises the specific, actionable codes (invalid_credentials /
    user_banned / user_suspended) and those are the only messages a caller
    sees. Anything that leaks an exception type or message ("User found
    during auth but not on second query") is a roadmap to our internals, so it
    goes to the server log instead of the response body.
    """
    throttle(
        request,
        "sign-in",
        settings.AUTH_IP_RATE_LIMIT,
        settings.AUTH_RATE_WINDOW_SECONDS,
        message="Too many sign-in attempts from this network. Try again in a few minutes.",
    )
    try:
        token = await auth_service.authenticate_user(db, user_in)
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(func.lower(UserModel.email) == user_in.email.lower().strip()))
        user = result.scalar_one_or_none()
        if not user:
            # Row vanished between auth and re-query (concurrent delete/ban).
            # Nobody should get a 500 with a stack-shaped message for that.
            logger.error("Sign-in: %s authenticated but the row vanished on re-query", user_in.email)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "temporarily_unavailable", "message": "We could not load your account. Try again in a moment."},
            )
        return await build_session_response(db, user, access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Sign-in failed for %s: %s", user_in.email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Sign-in could not be completed. Try again."},
        )

@router.post("/sign-out")
async def signout():
    return {"message": "Successfully signed out"}

@router.post("/forgot-password")
async def forgot_password(req: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Start a password reset. The public response is identical whether or
    not the account exists (no account enumeration).

    Delivery: no mail provider is bundled, so the link is written to the
    application log, which is the only channel that reaches a user today.
    Returning it in the API response is refused unless AUTH_DEV_RESET_RETURN
    is on *and* ENV is a dev value — the response body is readable by anyone
    who can reach the endpoint, which would make it a one-call account
    takeover for any address (see core/config.py).

    Throttling: per-network sliding window, plus a database-backed re-issue
    cooldown per address so retries cannot churn tokens.
    """
    throttle(
        request,
        "forgot-password",
        settings.AUTH_IP_RATE_LIMIT,
        settings.AUTH_RATE_WINDOW_SECONDS,
        message="Too many reset requests from this network. Please wait a few minutes.",
    )
    try:
        outcome = await auth_service.request_password_reset(
            db,
            req.email,
            reissue_cooldown_seconds=settings.AUTH_RESET_REISSUE_COOLDOWN_SECONDS,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Password reset request failed for %s: %s", req.email, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset request failed")

    if not outcome:
        return {"ok": True}

    user, raw_token = outcome
    if raw_token is None:
        logger.info(
            "Password reset re-request for %s suppressed by the %ss re-issue cooldown; the earlier link is still valid",
            user.email, settings.AUTH_RESET_REISSUE_COOLDOWN_SECONDS,
        )
        return {"ok": True}

    reset_url = f"{settings.PUBLIC_APP_BASE_URL}/reset-password?token={raw_token}"
    logger.warning(
        "PASSWORD RESET link issued for %s: %s (log delivery — no mail provider configured)",
        user.email, reset_url,
    )
    if settings.allow_reset_link_in_response:
        return {"ok": True, "reset_url": reset_url, "expires_in_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES}
    if getattr(settings, "AUTH_DEV_RESET_RETURN", False):
        logger.error(
            "AUTH_DEV_RESET_RETURN is enabled but ENV=%s, so the reset link was withheld from the response. "
            "Set AUTH_DEV_RESET_RETURN=false outside development.",
            settings.ENV,
        )
    return {"ok": True}

@router.post("/reset-password")
async def reset_password(req: PasswordResetConfirm, request: Request, db: AsyncSession = Depends(get_db)):
    """Redeem a reset token and set a new password. Returns a fresh session
    so the frontend can move straight into the app.

    A guessed token is worth exactly one try per network: this endpoint mints
    a session, so it gets the same throttle as sign-in.
    """
    throttle(
        request,
        "reset-password",
        settings.AUTH_IP_RATE_LIMIT,
        settings.AUTH_RATE_WINDOW_SECONDS,
        message="Too many reset attempts from this network. Please wait a few minutes.",
    )
    try:
        user = await auth_service.reset_password(db, req.token, req.new_password)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Password reset failed: %s", e)
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

@router.post("/webhook")
async def neon_auth_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Inbound user-sync from Neon/better-auth.

    This route provisions rows and opens a trial, so it is authenticated:
    the raw body must carry an HMAC-SHA256 signature matching
    NEON_WEBHOOK_SECRET, compared in constant time. If the secret is not
    configured the route refuses everything (503) rather than falling open —
    before this fix the signature was computed, logged in both forms, and
    never actually compared, which left user creation and trial grants open to
    any anonymous caller.

    Nothing about the signature is logged at any level: neither the received
    value, nor the expected digest, nor the secret.
    """
    throttle(
        request,
        "auth-webhook",
        settings.WEBHOOK_RATE_LIMIT,
        settings.WEBHOOK_RATE_WINDOW_SECONDS,
        message="Too many webhook deliveries. Slow down.",
    )

    if not settings.NEON_WEBHOOK_SECRET:
        logger.error("NEON_WEBHOOK_SECRET is not configured; rejecting /auth/webhook")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "webhook_not_configured", "message": "Webhook verification is not configured on this deployment."},
        )

    body = await request.body()
    signature = (
        request.headers.get("better-auth-signature")
        or request.headers.get("x-webhook-signature")
        or request.headers.get("x-signature")
    )
    if not verify_inbound_webhook_signature(settings.NEON_WEBHOOK_SECRET, body, signature):
        # Log the fact and the caller, never the values.
        logger.warning("Rejected /auth/webhook: signature missing or invalid (client=%s)", client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_signature", "message": "Webhook signature verification failed."},
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook envelope")

    event = payload.get("event")
    data = payload.get("data") or {}
    user_data = data.get("user") if isinstance(data, dict) else None
    if not isinstance(user_data, dict):
        return {"message": "Webhook received"}

    if event == "user.created" and user_data:
        user_id = user_data.get("id")
        email = user_data.get("email")
        name = user_data.get("name") or ""

        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Missing user_id or email")

        result = await db.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            now = datetime.datetime.now(datetime.timezone.utc)
            # settings.TRIAL_DAYS, not a literal: a trial provisioned through
            # Neon used to be 14 days while every other signup got 7.
            trial_expires = now + datetime.timedelta(days=int(settings.TRIAL_DAYS))

            new_user = User(
                id=user_id,
                email=str(email).strip().lower(),
                full_name=name or None,
                password_hash="EXTERNAL_AUTH_MANAGED",
                role="customer",
                trial_started_at=now,
                trial_expires_at=trial_expires,
            )
            db.add(new_user)
            await db.commit()

            await billing_service.get_or_create_default_org(db, new_user)

            return {"message": "User synchronized successfully"}

    return {"message": "Webhook received"}
