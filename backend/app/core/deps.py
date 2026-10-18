import math
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/signin", auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def _parse_revoked_at(value) -> Optional[float]:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def session_is_revoked(user: User, payload: dict) -> bool:
    """True when the token is outside the accepted class or behind the revocation boundary.

    Local and impersonation tokens carry ``ver``. Reset, logout, and ban increment
    ``token_version`` in the same write as ``sessions_revoked_at``, so a token
    minted earlier in that UTC second still has the old version and is rejected
    here. JWT ``iat`` is a whole second, so a fresh sign-in in that same second
    must not be rejected by the timestamp: its version already matches.
    External Neon tokens have no ``ver``. Their ``iat`` is still compared with
    ``<=`` against the full boundary.
    """
    metadata = getattr(user, "signup_metadata", None) or {}
    token_class = payload.get("_token_class")
    local = token_class != "external"
    token_ver = None
    current_ver = None
    if local:
        try:
            token_ver = int(payload.get("ver"))
            current_ver = int(metadata.get("token_version", 1))
        except (TypeError, ValueError):
            return True
        if token_ver < current_ver:
            return True
    revoked_at = _parse_revoked_at(metadata.get("sessions_revoked_at"))
    if revoked_at is None:
        return False
    try:
        issued_at = float(payload.get("iat"))
    except (TypeError, ValueError):
        return True
    if local and token_ver == current_ver:
        return issued_at < math.floor(revoked_at)
    return issued_at <= revoked_at


async def authenticate_bearer(db: AsyncSession, token: str) -> User:
    """The single bearer-token dependency used by routes and media access."""
    from app.core.security import verify_neon_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = await verify_neon_token(token)
    if not payload:
        raise credentials_exception
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_banned", "message": "This account has been banned."},
        )
    if getattr(user, "is_suspended", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_suspended", "message": "Account suspended"},
        )
    if session_is_revoked(user, payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_revoked", "message": "Session has been revoked. Please sign in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
        user._token_class = payload.get("_token_class")
    user._token_scope = payload.get("scope")
    user._actor_id = payload.get("act")
    await _bind_request_tenant(db, user)
    return user


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
        await _bind_request_tenant(db, user)
        return user

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await authenticate_bearer(db, token)

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

# Keys already mounted on admin routes. Anything else is denied for assistants.
ASSISTANT_PERMISSION_ALLOWLIST = frozenset({
    "overview",
    "jobs",
    "system",
    "plans",
    "organizations",
    "usage",
    "users",
    "support",
})


def require_admin_permission(permission_key: str):
    """
    Granular permission gate for admin endpoints (F80).
    - Full 'admin' role has all permissions unconditionally.
    - 'assistant-admin' is denied unless the key is on the allowlist and
      explicitly enabled. A missing flag is not permission.
    """
    async def _checker(current_user: User = Depends(get_current_admin)) -> User:
        if current_user.role == "admin":
            return current_user

        if permission_key not in ASSISTANT_PERMISSION_ALLOWLIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Assistant admin lacks '{permission_key}' permission."
            )

        perms = getattr(current_user, "admin_permissions", {}) or {}
        explicit = perms.get(permission_key)
        if explicit is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Assistant admin lacks '{permission_key}' permission."
            )
        sections = perms.get("sections")
        in_sections = isinstance(sections, (list, tuple)) and permission_key in sections
        if explicit is True or in_sections:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Assistant admin lacks '{permission_key}' permission."
        )
    return _checker


def require_feature(feature_name: str):
    """Server-side entitlement gate. Authentication alone is not paid access."""

    async def _checker(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        from app.services.billing_service import assert_can_spend

        await assert_can_spend(
            db,
            current_user,
            required_credits=0.0,
            feature_name=feature_name,
            lock_row=False,
        )
        return current_user

    return _checker


async def _bind_request_tenant(db: AsyncSession, user: User) -> None:
    from app.core.tenancy import apply_tenant_context, bind_tenant, get_user_org_ids

    scoped = getattr(user, "_scoped_org_id", None)
    org_ids = await get_user_org_ids(db, user)
    platform_admin = getattr(user, "role", None) == "admin" and not scoped
    bind_tenant(org_ids, user.id, platform_admin=platform_admin, enforce=True)
    await apply_tenant_context(db)
