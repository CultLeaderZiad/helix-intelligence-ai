from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
)
from app.core.config import settings
import uuid
import datetime
import hashlib
import secrets
import logging
import re
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _normalize_email(email: str) -> str:
    """Emails are matched and stored case-insensitively."""
    return str(email or "").strip().lower()


def _hash_reset_token(token: str) -> str:
    """We never store the raw reset token — only its SHA-256 digest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def authenticate_user(db: AsyncSession, user_in: UserLogin) -> str:
    if settings.USE_MOCKS:
        return create_access_token(subject="mock-admin-id", role="admin" if "admin" in user_in.email else "customer")

    email = _normalize_email(user_in.email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not await verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_banned", "message": "This account has been banned."}
        )
    if getattr(user, "is_suspended", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_suspended", "message": "This account has been suspended."}
        )

    metadata = getattr(user, "signup_metadata", None) or {}
    token_version = metadata.get("token_version", 1)
    return create_access_token(subject=user.id, role=user.role, token_version=token_version)

async def revoke_user_sessions(db: AsyncSession, user: User) -> int:
    """Increment the user's token version to immediately invalidate all existing sessions."""
    metadata = dict(user.signup_metadata or {})
    new_version = int(metadata.get("token_version", 1)) + 1
    # Version, not the fractional timestamp, splits two tokens inside one UTC
    # second. JWT iat cannot. The previous version stays revoked.
    metadata["token_version"] = new_version
    metadata["sessions_revoked_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    user.signup_metadata = metadata
    await db.commit()
    await db.refresh(user)
    return new_version

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    raw_name = (user_in.name or "").strip()
    full_name = raw_name if raw_name else None

    if settings.USE_MOCKS:
        return User(id=str(uuid.uuid4()), email=_normalize_email(user_in.email), password_hash="mock", role="customer", full_name=full_name)

    email = _normalize_email(user_in.email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")

    # Collect UTM and referral source attribution if present, sanitizing PII (F71)
    signup_metadata = {"token_version": 1}
    for field in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "referrer"):
        val = getattr(user_in, field, None)
        if val:
            s_val = str(val).strip()
            if field == "referrer" and (s_val.startswith("http://") or s_val.startswith("https://")):
                parts = urlsplit(s_val)
                s_val = parts._replace(query="", fragment="").geturl()
            # F71: Drop parameters containing email addresses to prevent PII leakage
            if _EMAIL_PATTERN.search(s_val):
                continue
            signup_metadata[field] = s_val

    if len(signup_metadata) > 1:
        # F71: Log anonymized attribution metadata without logging plain email alongside it
        logger.info("Attribution captured for signup: fields=%s", [k for k in signup_metadata if k != "token_version"])

    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        email=email,
        password_hash=get_password_hash(user_in.password),
        full_name=full_name,
        role="customer",
        signup_metadata=signup_metadata,
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7)
    )
    db.add(user)
    try:
        await db.flush()  # write user, get its id, don't commit yet
    except Exception as e:
        await db.rollback()
        err_msg = str(e).lower()
        if "unique" in err_msg or "integrity" in err_msg or "already exists" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
        logger.exception("Failed to flush new user record: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user account. Please try again.")

    # Seed the authenticated identity before creating its first organization;
    # the organizations policy permits only the owner_id/user_id bootstrap.
    from app.core.tenancy import apply_tenant_context, bind_tenant
    bind_tenant([], user.id, platform_admin=False, enforce=True)
    await apply_tenant_context(db)

    # Auto-create a personal org for every new user with 25 trial credits and default trial plan
    from app.models.organization import Organization
    org_name = full_name or user_in.email.split("@")[0]
    org = Organization(
        owner_id=user.id,
        name=f"{org_name}'s Workspace",
        plan_id="plan_trial_default",
        plan="trial",
        credit_balance=25.0,
        credits_used=0.0,
        daily_credits_used_today=0.0,
        images_generated_today=0.0,
        images_trial_total=0.0,
        videos_generated_today=0.0,
        status="active"
    )
    db.add(org)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        err_msg = str(e).lower()
        if "unique" in err_msg or "integrity" in err_msg or "already exists" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
        logger.exception("Failed to commit new user organization: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not initialize user workspace. Please try again.")
    bind_tenant([org.id], user.id, platform_admin=False, enforce=True)
    await apply_tenant_context(db)
    await db.refresh(user)   # reload all columns — caller must not access expired attrs in async context
    return user


async def request_password_reset(db: AsyncSession, email: str) -> User:
    """Mint a single-use reset token for the user. Callers must only call
    this for users that exist; the router handles the non-enumeration
    boundary and always returns the same public response either way."""
    email = _normalize_email(email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    raw_token = create_password_reset_token(user.id)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(
        minutes=int(settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    )
    user.password_reset_token_hash = _hash_reset_token(raw_token)
    user.password_reset_expires_at = expires
    await db.commit()
    return user, raw_token

async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    """Validate a reset token and set a new password. Returns the user, or
    raises 400 when the token is invalid, expired, or already used.
    
    Guarantees:
    - Atomic validation and consumption with row lock.
    - Stale or invalid links do NOT destroy newer active reset tokens (F18).
    - Password reset revokes all prior user sessions (F19).
    """
    payload = decode_password_reset_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."}
        )

    # Row lock user record during validation to prevent concurrent race condition (F18)
    result = await db.execute(
        select(User).where(User.id == payload["sub"]).with_for_update()
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_reset_token_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."}
        )

    token_hash = _hash_reset_token(token)
    if not secrets.compare_digest(token_hash, user.password_reset_token_hash):
        # STALE or MISMATCHED token: reject request, but DO NOT clear user.password_reset_token_hash.
        # This prevents stale links from invalidating newer links (F18).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."}
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    if user.password_reset_expires_at is not None:
        exp = user.password_reset_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        if exp.timestamp() < now.timestamp():
            # Current token is expired
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."}
            )

    # Atomically redeem token and set new password
    user.password_hash = get_password_hash(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.has_completed_onboarding = True

    # Revoke all previous sessions (F19). The version bump rejects a token
    # minted earlier in this same second; iat is only whole seconds.
    metadata = dict(user.signup_metadata or {})
    metadata["token_version"] = int(metadata.get("token_version", 1)) + 1
    metadata["password_reset_at"] = now.isoformat()
    metadata["sessions_revoked_at"] = now.isoformat()
    user.signup_metadata = metadata

    await db.commit()
    await db.refresh(user)
    return user
