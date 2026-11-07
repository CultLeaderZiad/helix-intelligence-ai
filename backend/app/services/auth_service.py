import asyncio
import collections
import time
from typing import Optional

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
    token, _user = await authenticate_user_and_load(db, user_in)
    return token


# --- Failed sign-in throttle -------------------------------------------------
# Per account, stored on the user row so it holds across processes and is not
# keyed on a client IP (which a proxy can hide and an attacker can rotate).
# Unknown emails are counted in process memory so they get the same answer as
# real accounts and do not reveal which emails are registered.
_FAILED_KEY = "failed_sign_ins"
_FAILED_SINCE_KEY = "failed_sign_ins_since"
_LOCKED_UNTIL_KEY = "sign_in_locked_until"
_UNKNOWN_FAILURES: "collections.OrderedDict[str, list[float]]" = collections.OrderedDict()
_UNKNOWN_FAILURES_MAX = 10_000


def _throttle_exception(retry_after_s: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "too_many_sign_in_attempts",
            "message": "Too many sign-in attempts. Wait a few minutes, or reset your password.",
        },
        headers={"Retry-After": str(max(1, int(retry_after_s)))},
    )


def _parse_iso(value) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def _locked_for(user: User, now: datetime.datetime) -> int:
    """Seconds left on this account's sign-in lock, 0 when unlocked."""
    until = _parse_iso((user.signup_metadata or {}).get(_LOCKED_UNTIL_KEY))
    if until is None or until <= now:
        return 0
    return int((until - now).total_seconds()) + 1


def _unknown_email_failure(email: str) -> bool:
    """Count a failure for an email with no account; True once it is throttled."""
    now = time.monotonic()
    window = settings.SIGN_IN_FAILURE_WINDOW_S
    hits = [t for t in _UNKNOWN_FAILURES.pop(email, []) if now - t < window]
    hits.append(now)
    _UNKNOWN_FAILURES[email] = hits
    while len(_UNKNOWN_FAILURES) > _UNKNOWN_FAILURES_MAX:
        _UNKNOWN_FAILURES.popitem(last=False)
    return len(hits) >= settings.SIGN_IN_FAILURE_LIMIT


def _unknown_email_throttled(email: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _UNKNOWN_FAILURES.get(email, []) if now - t < settings.SIGN_IN_FAILURE_WINDOW_S]
    return len(hits) >= settings.SIGN_IN_FAILURE_LIMIT


async def _record_failed_sign_in(db: AsyncSession, user_id: str, now: datetime.datetime) -> int:
    """Count one failure under a row lock. Returns seconds locked (0 if not locked)."""
    locked = (
        await db.execute(
            select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one()
    metadata = dict(locked.signup_metadata or {})
    since = _parse_iso(metadata.get(_FAILED_SINCE_KEY))
    window = datetime.timedelta(seconds=settings.SIGN_IN_FAILURE_WINDOW_S)
    if since is None or now - since > window:
        metadata[_FAILED_SINCE_KEY] = now.isoformat()
        metadata[_FAILED_KEY] = 0
    metadata[_FAILED_KEY] = int(metadata.get(_FAILED_KEY) or 0) + 1
    lock_s = 0
    if metadata[_FAILED_KEY] >= settings.SIGN_IN_FAILURE_LIMIT:
        lock_s = settings.SIGN_IN_LOCK_S
        metadata[_LOCKED_UNTIL_KEY] = (now + datetime.timedelta(seconds=lock_s)).isoformat()
        metadata[_FAILED_KEY] = 0
        metadata[_FAILED_SINCE_KEY] = None
    locked.signup_metadata = metadata
    await db.commit()
    return lock_s


def _clear_throttle(metadata: dict) -> dict:
    for key in (_FAILED_KEY, _FAILED_SINCE_KEY, _LOCKED_UNTIL_KEY):
        metadata.pop(key, None)
    return metadata


async def authenticate_user_and_load(db: AsyncSession, user_in: UserLogin) -> tuple[str, Optional[User]]:
    """Verify credentials and return the token with the user row already loaded,
    so callers do not query the same user a second time.

    An account locked by repeated failures is refused before its password is
    checked, so guessing makes no progress while the lock lasts.
    """
    email = _normalize_email(user_in.email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()
    now = datetime.datetime.now(datetime.timezone.utc)

    if not user:
        if _unknown_email_throttled(email):
            raise _throttle_exception(settings.SIGN_IN_LOCK_S)
        if _unknown_email_failure(email):
            raise _throttle_exception(settings.SIGN_IN_LOCK_S)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    remaining = _locked_for(user, now)
    if remaining:
        raise _throttle_exception(remaining)
    if not await verify_password(user_in.password, user.password_hash):
        lock_s = await _record_failed_sign_in(db, user.id, now)
        if lock_s:
            logger.warning("Sign-in locked after repeated failures: user=%s", user.id)
            raise _throttle_exception(lock_s)
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
    if any(key in metadata for key in (_FAILED_KEY, _FAILED_SINCE_KEY, _LOCKED_UNTIL_KEY)):
        user.signup_metadata = _clear_throttle(dict(metadata))
        await db.commit()
        await db.refresh(user)
        metadata = user.signup_metadata or {}
    return session_token_for(user), user


def session_token_for(user: User) -> str:
    """Mint a session token. Admin sessions use the shorter admin lifetime."""
    metadata = getattr(user, "signup_metadata", None) or {}
    token_version = metadata.get("token_version", 1)
    expires = None
    if getattr(user, "is_platform_admin", False) or getattr(user, "role", None) in ("admin", "assistant-admin"):
        expires = datetime.timedelta(minutes=settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        subject=user.id, role=user.role, token_version=token_version, expires_delta=expires
    )

async def revoke_user_sessions(db: AsyncSession, user: User, *, commit: bool = True) -> int:
    """Increment the user's token version to immediately invalidate all existing sessions."""
    metadata = dict(user.signup_metadata or {})
    new_version = int(metadata.get("token_version", 1)) + 1
    # Version, not the fractional timestamp, splits two tokens inside one UTC
    # second. JWT iat cannot. The previous version stays revoked.
    metadata["token_version"] = new_version
    metadata["sessions_revoked_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    user.signup_metadata = metadata
    if commit:
        await db.commit()
        await db.refresh(user)
    return new_version

class EmailAlreadyRegistered(Exception):
    """Internal signal only. The sign-up route answers identically either way."""


async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    raw_name = (user_in.name or "").strip()
    full_name = raw_name if raw_name else None

    email = _normalize_email(user_in.email)
    # PBKDF2 runs off the event loop, and also for an existing email, so the
    # duplicate path costs the same time as a real registration.
    password_hash = await asyncio.to_thread(get_password_hash, user_in.password)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    if result.scalar_one_or_none():
        raise EmailAlreadyRegistered()

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

    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role="customer",
        signup_metadata=signup_metadata
    )
    db.add(user)
    try:
        await db.flush()  # write user, get its id, don't commit yet
    except Exception as e:
        await db.rollback()
        err_msg = str(e).lower()
        if "unique" in err_msg or "integrity" in err_msg or "already exists" in err_msg:
            raise EmailAlreadyRegistered() from None
        logger.exception("Failed to flush new user record: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user account. Please try again.")

    # Seed the authenticated identity before creating its first organization;
    # the organizations policy permits only the owner_id/user_id bootstrap.
    from app.core.tenancy import apply_tenant_context, bind_tenant
    bind_tenant([], user.id, platform_admin=False, enforce=True)
    await apply_tenant_context(db)

    # Every new user gets a personal workspace on the default plan. It stays
    # pending (all features off) until a platform admin grants access.
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
            raise EmailAlreadyRegistered() from None
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
    # A completed reset proves control of the inbox, so it ends any sign-in lock.
    user.signup_metadata = _clear_throttle(metadata)

    await db.commit()
    await db.refresh(user)
    return user
