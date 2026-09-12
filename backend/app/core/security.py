import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import httpx
from jose import jwt, JWTError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

ALGORITHM = "RS256"  # Neon JWKS issues RS256 JWTs by default
HS256_ALGORITHM = "HS256"

_jwks_cache = None

async def get_jwks_keys():
    """Fetch and cache JWKS keys from Neon Auth."""
    global _jwks_cache
    if _jwks_cache is None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.NEON_JWKS_URL)
                response.raise_for_status()
                _jwks_cache = response.json()
                logger.info(f"Loaded JWKS keys from {settings.NEON_JWKS_URL}")
        except Exception as e:
            logger.error(f"Failed to load JWKS: {e}")
            raise ValueError("Authentication service unavailable")
    return _jwks_cache

async def verify_neon_token(token: str) -> dict:
    """Validate a token against local HS256 secret or Neon Auth JWKS and return the decoded payload."""
    # 1. First try local HS256 secret (for local tokens / seed sessions)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[HS256_ALGORITHM], options={"verify_aud": False})
        if payload and payload.get("sub") and payload.get("purpose") != "password_reset":
            return payload
    except Exception:
        pass

    # 2. Fall back to Neon JWKS RS256
    try:
        jwks = await get_jwks_keys()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}  # Neon might not set 'aud' natively
        )
        return payload
    except Exception as e:
        logger.warning(f"JWT Validation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Webhook authentication
#
# Two independent mechanisms, both constant-time:
#
# 1. ``verify_inbound_webhook_signature`` — inbound shared-secret HMAC (used by
#    /auth/webhook, the Neon/better-auth user-sync route).
# 2. ``sign_job_webhook_token`` / ``verify_job_webhook_token`` — a capability
#    token we mint per media job and put in the callback URL we hand to the
#    generation provider, so a callback can only ever touch the job it was
#    created for. A provider that simply POSTs our URL cannot forge or replay
#    against someone else's job.
#
# Neither helper may ever log the secret, the expected digest, or a valid
# token: a signature in a log line is a bearer credential that survives the
# request.
# ---------------------------------------------------------------------------

_WEBHOOK_TOKEN_SCOPE = "media-job-webhook"


def compute_webhook_signature(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_inbound_webhook_signature(secret: str, raw_body: bytes, provided: Optional[str]) -> bool:
    """Constant-time compare of the caller's signature against the HMAC.

    Accepts a bare hex digest or the ``t=..,v1=<hex>`` / ``v1=<hex>`` prefixes
    some senders use. Returns False for anything missing or malformed; never
    raises and never echoes either side.
    """
    if not secret or not provided:
        return False
    candidate = provided.strip()
    if "=" in candidate:
        # Take the last comma-separated segment's value (Stripe-style lists).
        parts = [p.strip() for p in candidate.split(",") if p.strip()]
        candidate = parts[-1].split("=", 1)[1] if parts and "=" in parts[-1] else candidate
    expected = compute_webhook_signature(secret, raw_body)
    return hmac.compare_digest(candidate.lower(), expected.lower())


def sign_job_webhook_token(job_id: str) -> str:
    payload = f"{_WEBHOOK_TOKEN_SCOPE}:{job_id}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()[:32]


def verify_job_webhook_token(job_id: str, token: Optional[str]) -> bool:
    if not token:
        return False
    return hmac.compare_digest(sign_job_webhook_token(job_id), token.strip())


def create_access_token(subject: Union[str, Any], role: str = "customer", expires_delta: timedelta = None) -> str:
    """Create local HS256 JWT token."""
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=HS256_ALGORITHM)
    return encoded_jwt

def create_password_reset_token(user_id: str) -> str:
    """Single-purpose, short-lived JWT for the password reset flow.

    Has a distinct `purpose` claim so it can never be accepted as a session
    token, and a short lifetime so a leaked reset link is quickly unusable.
    """
    expire_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 30))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "purpose": "password_reset",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=HS256_ALGORITHM)

def decode_password_reset_token(token: str) -> Union[dict, None]:
    """Return the payload only for a valid, unexpired password_reset token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[HS256_ALGORITHM], options={"verify_aud": False})
    except JWTError:
        return None
    if payload.get("purpose") != "password_reset" or not payload.get("sub"):
        return None
    return payload

# ---------------------------------------------------------------------------
# Password hashing
#
# P2 follow-up, deliberately NOT fixed in this change set (noted here so it is
# not re-discovered by an audit): the hash itself is fine — PBKDF2-HMAC-SHA256,
# 100k iterations, random per-user salt, constant-time compare. The problem is
# *where* it runs. `verify_password` is declared async but calls the blocking
# hashlib work inline, so a login costs ~33 ms on this sandbox CPU (expect
# 60-100 ms on Render's 0.5 vCPU) taken straight off the one event-loop thread
# that also serves every other in-flight request. A credential-stuffing burst
# therefore stalls the whole worker, including the long-poll endpoints.
#
# The fix, when it gets its own change: `await anyio.to_thread.run_sync(...)`
# around the hash/verify calls (bcrypt is already a dependency, and the stored
# format carries its own algorithm prefix, so old rows can be upgraded lazily
# on next successful sign-in). It needs a real before/after latency check under
# concurrency, which is why it does not belong in a security-correctness PR.
# ---------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    """Secure password hashing using PBKDF2-HMAC-SHA256 (Python 3.12-3.14 native)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    if not hashed_password or not plain_password:
        return False
    try:
        if hashed_password.startswith("pbkdf2:sha256:"):
            parts = hashed_password.split("$")
            if len(parts) != 3:
                return False
            iterations = int(parts[0].split(":")[2])
            salt = parts[1]
            expected_key = parts[2]
            key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
            return secrets.compare_digest(key.hex(), expected_key)
        else:
            # Fallback for plain or legacy hash formats
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return secrets.compare_digest(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False
