from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, SessionResponse
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
import hmac
import logging

logger = logging.getLogger(__name__)


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

    return create_access_token(subject=user.id, role=user.role)

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    if settings.USE_MOCKS:
        return User(id=str(uuid.uuid4()), email=_normalize_email(user_in.email), password_hash="mock", role="customer")

    email = _normalize_email(user_in.email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        email=email,
        password_hash=get_password_hash(user_in.password),
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
    await db.refresh(user)   # reload all columns — caller must not access expired attrs in async context
    return user

async def request_password_reset(db: AsyncSession, email: str, *, reissue_cooldown_seconds: int = 0):
    """Mint a single-use reset token for the user. Callers must only call
    this for users that exist; the router handles the non-enumeration
    boundary and always returns the same public response either way.

    ``reissue_cooldown_seconds`` > 0 leaves an already-issued, still-valid link
    alone instead of minting a replacement on every click: repeated requests
    from a bot (or an impatient user) cannot churn the token store, and the
    first link keeps working. Returns ``(user, raw_token)``, where ``raw_token``
    is None when the cooldown suppressed the re-issue.
    """
    email = _normalize_email(email)
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    if reissue_cooldown_seconds > 0 and _reset_issued_within(user, reissue_cooldown_seconds):
        return user, None

    raw_token = create_password_reset_token(user.id)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(
        minutes=int(settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    )
    user.password_reset_token_hash = _hash_reset_token(raw_token)
    user.password_reset_expires_at = expires
    await db.commit()
    return user, raw_token


def _reset_issued_within(user: User, seconds: int) -> bool:
    """True when a live reset link was minted less than ``seconds`` ago.

    Derived from the expiry column (issued_at = expires_at - TTL) so no extra
    state or migration is needed; an expired link is deliberately *not*
    throttled, otherwise one ignored email would lock the address out of ever
    requesting another.
    """
    if not user.password_reset_expires_at or not user.password_reset_token_hash:
        return False
    ttl_seconds = int(settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES) * 60
    expires_at = user.password_reset_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    issued_at = expires_at - datetime.timedelta(seconds=ttl_seconds)
    return issued_at > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds)


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    """Validate a reset token and set a new password. Returns the user, or
    raises 400 when the token is invalid, expired, or already used."""
    payload = decode_password_reset_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."})

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."})

    if not user.password_reset_token_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."})

    # Constant-time: this compares a secret digest against a caller-supplied
    # value, which is exactly the shape that must not short-circuit.
    hash_ok = hmac.compare_digest(_hash_reset_token(token), user.password_reset_token_hash or "")
    if user.password_reset_expires_at is not None:
        exp = user.password_reset_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        if exp.timestamp() < datetime.datetime.now(datetime.timezone.utc).timestamp():
            hash_ok = False

    if not hash_ok:
        # Burn the stored token either way so a guessed/stale link can't be retried.
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "This reset link is invalid or has expired. Please request a new one."})

    user.password_hash = get_password_hash(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.has_completed_onboarding = True
    await db.commit()
    await db.refresh(user)
    return user
