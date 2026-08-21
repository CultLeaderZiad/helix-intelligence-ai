from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.schemas.auth import UserCreate, UserLogin, SessionResponse
from app.services import auth_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/sign-up", response_model=SessionResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(db, user_in)
    # Generate token directly — no need to re-query + re-verify the password we just hashed
    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, role=user.role)
    return SessionResponse(user_id=user.id, email=user.email, role=user.role, access_token=token)

@router.post("/sign-in", response_model=SessionResponse)
async def signin(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    token = await auth_service.authenticate_user(db, user_in)
    # Fetch user to get id, email, role for the session response
    from sqlalchemy import select
    from app.models.user import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.email == user_in.email))
    user = result.scalar_one_or_none()
    return SessionResponse(user_id=user.id, email=user.email, role=user.role, access_token=token)

@router.post("/sign-out")
async def signout():
    # Typically handled on client side for JWT
    return {"message": "Successfully signed out"}

@router.get("/session", response_model=SessionResponse)
async def get_session(current_user: User = Depends(get_current_user)):
    return SessionResponse(user_id=current_user.id, email=current_user.email, role=current_user.role)
