from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    plan = (await db.execute(select(Plan).where(Plan.id == org.plan_id))).scalar_one_or_none()
    if not plan:
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
    if not plan:
        # Fallback: return a minimal session without plan data instead of crashing
        return SessionResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            access_token=access_token,
            feature_flags={},
            credit_balance=round(float(org.credit_balance), 2),
            trial_days_remaining=None,
            daily_credit_limit=None,
            daily_credits_used=0,
            daily_credits_remaining=None,
            daily_credits_resets_at_utc=None,
            plan_id=org.plan_id,
            has_completed_onboarding=getattr(user, "has_completed_onboarding", False)
        )

    effective_flags = dict(plan.feature_flags or {})
    if org.custom_feature_flags:
        effective_flags.update(org.custom_feature_flags)

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    trial_days_remaining = None
    if user.trial_expires_at:
        trial_exp = user.trial_expires_at
        if trial_exp.tzinfo is None:
            trial_exp = trial_exp.replace(tzinfo=datetime.timezone.utc)
        trial_days_remaining = max(0, (trial_exp - now).days) if trial_exp > now else 0

    # Daily usage info
    from app.services.billing_service import _ensure_daily_reset, _utc_midnight
    await _ensure_daily_reset(db, org)
    daily_limit = getattr(plan, "daily_credit_limit", None)
    daily_used = round(float(org.daily_credits_used_today), 2)
    daily_remaining = round(max(0, (daily_limit or 0) - daily_used), 2) if daily_limit else None
    daily_resets_at = None
    if daily_limit:
        daily_resets_at = (_utc_midnight(now) + datetime.timedelta(days=1)).isoformat()

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        feature_flags=effective_flags,
        credit_balance=round(float(org.credit_balance), 2),
        trial_days_remaining=trial_days_remaining,
        daily_credit_limit=daily_limit,
        daily_credits_used=daily_used,
        daily_credits_remaining=daily_remaining,
        daily_credits_resets_at_utc=daily_resets_at,
        plan_id=org.plan_id,
        has_completed_onboarding=getattr(user, "has_completed_onboarding", False)
    )

@router.post("/sign-up", response_model=SessionResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(db, user_in)
    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, role=user.role)
    return await build_session_response(db, user, access_token=token)

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during sign-in")

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
