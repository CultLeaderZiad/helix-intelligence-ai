import asyncio
import hmac
import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import httpx
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "RS256"  # Neon JWKS issues RS256 JWTs by default
HS256_ALGORITHM = "HS256"
LOCAL_TOKEN_USES = {"session", "impersonation"}

_jwks_lock = asyncio.Lock()
_jwks_cache: dict[str, tuple[float, dict]] = {}
_jwks_refresh_times: list[float] = []
_JWKS_CACHE_TTL_SECONDS = 3600.0


def reset_jwks_cache() -> None:
    """Test helper. Clears the in-process JWKS cache and refresh budget."""
    _jwks_cache.clear()
    _jwks_refresh_times.clear()


def _jwks_has_kid(jwks: Optional[dict], kid: Optional[str]) -> bool:
    if not jwks or not kid:
        return False
    return any(item.get("kid") == kid for item in (jwks.get("keys") or []))


async def _fetch_jwks(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0, trust_env=False, follow_redirects=False) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise ValueError("Authentication service unavailable")
    return payload


async def get_jwks_keys(url: Optional[str] = None, unknown_kid: Optional[str] = None, force_refresh: bool = False):
    """Fetch JWKS. Network refresh happens for a cold cache or an unknown key id.

    Unknown-kid refreshes are single-flight and rate limited. Signature failures
    for a key id that is already cached do not trigger a refresh.
    ``force_refresh`` remains as a compatibility alias for an unknown-kid refresh.
    """
    target = (url or settings.NEON_JWKS_URL or "").strip()
    if not target:
        raise ValueError("Authentication service unavailable")
    if force_refresh and unknown_kid is None:
        unknown_kid = "__force__"
    async with _jwks_lock:
        now = time.time()
        cached = _jwks_cache.get(target)
        fresh = cached is not None and now < cached[0]
        if unknown_kid is None:
            if fresh:
                return cached[1]
        elif cached and unknown_kid != "__force__" and _jwks_has_kid(cached[1], unknown_kid):
            return cached[1]
        else:
            window = float(getattr(settings, "JWKS_REFRESH_WINDOW_S", 60))
            limit = int(getattr(settings, "JWKS_REFRESH_LIMIT", 8))
            _jwks_refresh_times[:] = [stamp for stamp in _jwks_refresh_times if now - stamp < window]
            if len(_jwks_refresh_times) >= limit:
                logger.warning("JWKS refresh rate limit reached for %s", target)
                if cached:
                    return cached[1]
                raise ValueError("Authentication service unavailable")
            _jwks_refresh_times.append(now)
        try:
            payload = await _fetch_jwks(target)
        except Exception as exc:
            logger.error("Failed to load JWKS from %s: %s", target, exc)
            if cached:
                return cached[1]
            raise ValueError("Authentication service unavailable") from exc
        _jwks_cache[target] = (now + _JWKS_CACHE_TTL_SECONDS, payload)
        logger.info("Loaded JWKS keys from %s", target)
        return payload


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


async def _verify_external_session(token: str, header: dict) -> Optional[dict]:
    kid = header.get("kid")
    if not kid or not settings.NEON_JWT_ISSUER or not settings.NEON_JWT_AUDIENCE:
        return None
    try:
        jwks = await get_jwks_keys()
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        return None
    if not _jwks_has_kid(jwks, kid):
        try:
            jwks = await get_jwks_keys(unknown_kid=str(kid))
        except Exception as exc:
            logger.warning("JWT validation failed: %s", exc)
            return None
        if not _jwks_has_kid(jwks, kid):
            return None
    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=[ALGORITHM],
            audience=settings.NEON_JWT_AUDIENCE,
            issuer=settings.NEON_JWT_ISSUER,
        )
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        return None
    if not payload.get("sub") or payload.get("iat") is None:
        return None
    decoded = dict(payload)
    decoded["_token_class"] = "external"
    return decoded


async def verify_neon_token(token: str) -> Optional[dict]:
    """Validate a local session or an external Neon session.

    Local tokens must carry issuer, audience, and a session version. Versionless
    local tokens are rejected. External tokens must match the configured issuer
    and audience. JWKS is refreshed only when the key id is not cached.
    """
    if not token:
        return None
    header = _unverified_header(token)
    if not header:
        return None
    algorithm = header.get("alg")
    if algorithm == HS256_ALGORITHM:
        return _verify_local_session(token)
    if algorithm == ALGORITHM:
        return await _verify_external_session(token, header)
    return None


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
