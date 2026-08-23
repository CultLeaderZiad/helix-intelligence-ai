from fastapi import APIRouter, Depends
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
        plan = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one()

    effective_flags = dict(plan.feature_flags or {})
    if org.custom_feature_flags:
        effective_flags.update(org.custom_feature_flags)

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        feature_flags=effective_flags,
        credit_balance=round(float(org.credit_balance), 2),
        plan_id=org.plan_id
    )

@router.post("/sign-up", response_model=SessionResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(db, user_in)
    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, role=user.role)
    return await build_session_response(db, user, access_token=token)

@router.post("/sign-in", response_model=SessionResponse)
async def signin(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    token = await auth_service.authenticate_user(db, user_in)
    from app.models.user import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.email == user_in.email))
    user = result.scalar_one_or_none()
    return await build_session_response(db, user, access_token=token)

@router.post("/sign-out")
async def signout():
    return {"message": "Successfully signed out"}

@router.get("/session", response_model=SessionResponse)
async def get_session(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await build_session_response(db, current_user)
