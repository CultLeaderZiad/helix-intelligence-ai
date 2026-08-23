from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, SessionResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
import uuid
import datetime
async def authenticate_user(db: AsyncSession, user_in: UserLogin) -> str:
    if settings.USE_MOCKS:
        return create_access_token(subject="mock-admin-id", role="admin" if "admin" in user_in.email else "customer")

    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not await verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    return create_access_token(subject=user.id, role=user.role)

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    if settings.USE_MOCKS:
        return User(id=str(uuid.uuid4()), email=user_in.email, password_hash="mock", role="customer")

    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        email=user_in.email,
        password_hash=await get_password_hash(user_in.password),
        role="customer",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7)
    )
    db.add(user)
    await db.flush()  # write user, get its id, don't commit yet

    # Auto-create a personal org for every new user with 25 trial credits and default trial plan
    from app.models.organization import Organization
    org_name = getattr(user_in, "name", None) or user_in.email.split("@")[0]
    org = Organization(
        owner_id=user.id,
        name=f"{org_name}'s Workspace",
        plan_id="plan_trial_default",
        plan="trial",
        credit_balance=25.0,
        credits_used=0.0,
        status="active"
    )
    db.add(org)
    await db.commit()
    return user
