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
