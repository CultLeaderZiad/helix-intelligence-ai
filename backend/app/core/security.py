import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

HS256_ALGORITHM = "HS256"
LOCAL_TOKEN_USES = {"session", "impersonation"}


def _unverified_header(token: str) -> Optional[dict]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        return None
    return header if isinstance(header, dict) else None


def _verify_local_session(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[HS256_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        return None
    if payload.get("purpose") == "password_reset":
        return None
    token_use = payload.get("token_use") or "session"
    if token_use not in LOCAL_TOKEN_USES:
        return None
    if payload.get("ver") is None or not payload.get("sub") or payload.get("iat") is None:
        return None
    decoded = dict(payload)
    decoded["_token_class"] = "impersonation" if token_use == "impersonation" else "local"
    return decoded


async def verify_session_token(token: str) -> Optional[dict]:
    """Validate a Helix session (or impersonation) token.

    Tokens are HS256 with issuer, audience and a session version. Versionless
    tokens and every other algorithm are rejected. Helix does not accept
    externally issued identity tokens.
    """
    if not token:
        return None
    header = _unverified_header(token)
    if not header or header.get("alg") != HS256_ALGORITHM:
        return None
    return _verify_local_session(token)


def create_access_token(
    subject: Union[str, Any],
    role: str = "customer",
    expires_delta: timedelta = None,
    token_version: int = 1,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a local HS256 session token with issuer, audience, and version."""
    now = datetime.now(timezone.utc)
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
    expire = now + expires_delta if expires_delta else now + timedelta(minutes=expire_minutes)
    to_encode = {
        "exp": expire,
        "iat": int(now.timestamp()),
        "sub": str(subject),
        "role": role,
        "ver": int(token_version or 1),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "token_use": "session",
    }
    for key, value in (extra_claims or {}).items():
        if key in {"exp", "iat", "sub", "iss", "aud", "ver"}:
            continue
        to_encode[key] = value
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=HS256_ALGORITHM)


def create_password_reset_token(user_id: str) -> str:
    """Single-purpose, short-lived JWT for the password reset flow.

    Has a distinct `purpose` claim so it can never be accepted as a session
    token, a cryptographic `jti`, and a short lifetime.
    """
    expire_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 30))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode = {
        "exp": expire,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "sub": str(user_id),
        "purpose": "password_reset",
        "jti": secrets.token_urlsafe(16),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=HS256_ALGORITHM)


def decode_password_reset_token(token: str) -> Union[dict, None]:
    """Return the payload only for a valid, unexpired password_reset token."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[HS256_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
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
    from app.core.timing import aspan
    async with aspan("hash"):
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
