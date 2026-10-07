from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Header, Security, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_maker
from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/signin", auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> User:
    # 1. Check API Key authentication
    if isinstance(x_api_key, str) and x_api_key.strip():
        from app.services.api_key_service import authenticate_api_key
        user, org = await authenticate_api_key(db, x_api_key)
        user._scoped_org_id = org.id
        if getattr(user, "is_banned", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "user_banned", "message": "This account has been banned."}
            )
        if getattr(user, "is_suspended", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "user_suspended", "message": "Account suspended"}
            )
        return user

    # 2. Check JWT Bearer token authentication
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    from app.core.security import verify_neon_token
    payload = await verify_neon_token(token)
    
    if not payload:
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception

    if getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_banned", "message": "This account has been banned."}
        )

    if getattr(user, "is_suspended", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_suspended", "message": "Account suspended"}
        )

    # Check session revocation (F19)
    token_ver = payload.get("ver")
    if token_ver is not None:
        metadata = getattr(user, "signup_metadata", None) or {}
        current_ver = metadata.get("token_version", 1)
        if int(token_ver) < int(current_ver):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "session_revoked", "message": "Session has been revoked. Please sign in again."},
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Allows full 'admin' and 'assistant-admin' for support/view tasks."""
    if current_user.role not in ["admin", "assistant-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_current_full_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Strictly requires full 'admin' for plan/pricing editing and dangerous actions."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires full administrator privileges"
        )
    return current_user

async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[User]:
    """Returns the authenticated User if valid credentials are provided, else None without raising 401."""
    if not token and not (isinstance(x_api_key, str) and x_api_key.strip()):
        return None
    try:
        return await get_current_user(db=db, token=token, x_api_key=x_api_key)
    except HTTPException:
        return None

def require_admin_permission(permission_key: str):
    """
    Granular permission gate for admin endpoints (F80).
    - Full 'admin' role has all permissions unconditionally.
    - 'assistant-admin' must have permission_key enabled in user.admin_permissions.
    """
    async def _checker(current_user: User = Depends(get_current_admin)) -> User:
        if current_user.role == "admin":
            return current_user

        perms = getattr(current_user, "admin_permissions", {}) or {}
        # Explicit false checks (e.g. perms["users"] == False or perms["can_view_users"] == False)
        if (
            perms.get(permission_key) is False
            or perms.get(f"can_{permission_key}") is False
            or perms.get(f"can_view_{permission_key}") is False
            or perms.get(f"can_manage_{permission_key}") is False
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Assistant admin lacks '{permission_key}' permission."
            )
        if "sections" in perms and permission_key not in perms["sections"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Assistant admin lacks '{permission_key}' permission."
            )
        return current_user
    return _checker
