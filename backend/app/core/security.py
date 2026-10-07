import hmac
import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union
import httpx
from jose import jwt, JWTError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

import time

ALGORITHM = "RS256"  # Neon JWKS issues RS256 JWTs by default
HS256_ALGORITHM = "HS256"

_jwks_cache = None
_jwks_cache_expiry = 0.0
_JWKS_CACHE_TTL_SECONDS = 3600.0  # 1 hour TTL

async def get_jwks_keys(force_refresh: bool = False):
    """Fetch and cache JWKS keys from Neon Auth with TTL and force-refresh support."""
    global _jwks_cache, _jwks_cache_expiry
    now = time.time()
    if force_refresh or _jwks_cache is None or now >= _jwks_cache_expiry:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(settings.NEON_JWKS_URL)
                response.raise_for_status()
                _jwks_cache = response.json()
                _jwks_cache_expiry = now + _JWKS_CACHE_TTL_SECONDS
                logger.info(f"Loaded JWKS keys from {settings.NEON_JWKS_URL}")
        except Exception as e:
            logger.error(f"Failed to load JWKS: {e}")
            if _jwks_cache is not None:
                # If network fails but we had a cache, serve stale cache as fallback
                return _jwks_cache
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

    # 2. Fall back to Neon JWKS RS256 with auto-refresh on unknown kid (key rotation)
    try:
        jwks = await get_jwks_keys()
        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=[ALGORITHM],
                options={"verify_aud": False}
            )
            return payload
        except Exception:
            # Key rotation: if validation failed with cached keys, force a refresh once
            jwks = await get_jwks_keys(force_refresh=True)
            payload = jwt.decode(
                token,
                jwks,
                algorithms=[ALGORITHM],
                options={"verify_aud": False}
            )
            return payload
    except Exception as e:
        logger.warning(f"JWT Validation failed: {e}")
        return None

def create_access_token(
    subject: Union[str, Any],
    role: str = "customer",
    expires_delta: timedelta = None,
    token_version: int = 1
) -> str:
    """Create local HS256 JWT token with session versioning."""
    now = datetime.now(timezone.utc)
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=expire_minutes)
    
    to_encode = {
        "exp": expire,
        "iat": int(now.timestamp()),
        "sub": str(subject),
        "role": role,
        "ver": int(token_version or 1),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=HS256_ALGORITHM)
    return encoded_jwt

def create_password_reset_token(user_id: str) -> str:
    """Single-purpose, short-lived JWT for the password reset flow.

    Has a distinct `purpose` claim so it can never be accepted as a session
    token, a cryptographic `jti`, and a short lifetime.
    """
    expire_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 30))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "purpose": "password_reset",
        "jti": secrets.token_urlsafe(16),
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

def get_password_hash(password: str) -> str:
    """Secure password hashing using PBKDF2-HMAC-SHA256 (Python 3.12-3.14 native)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"

def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Blocking verification — run via asyncio.to_thread so the event loop is
    never stalled by PBKDF2's 100k iterations (a DoS amplifier on auth)."""
    if not hashed_password or not plain_password:
        return False

    # Accounts managed via external auth (OAuth/Neon) have no local password.
    # Disallow any login attempt with external-auth markers or non-hash strings.
    if hashed_password.startswith("EXTERNAL_AUTH") or hashed_password == "EXTERNAL_AUTH_MANAGED":
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
        elif hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            # Fallback for legacy bcrypt hash formats
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        else:
            # Non-hash marker or unsupported format: never compare plaintext
            return False
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash, off the event loop."""
    import asyncio
    return await asyncio.to_thread(_verify_password_sync, plain_password, hashed_password)

def verify_hmac_signature(body: bytes, signature: str, secret: str) -> bool:
    """Constant-time HMAC-SHA256 check for inbound webhook signatures.

    Accepts a raw hex digest or a `sha256=<hex>` prefixed header value.
    Returns False (never raises) for any missing/blank input, so callers can
    treat "unverified" and "malformed" identically.
    """
    if not body or not signature or not secret:
        return False
    sig = signature.strip()
    if sig.lower().startswith("sha256="):
        sig = sig[7:]
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
