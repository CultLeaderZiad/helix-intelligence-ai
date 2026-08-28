from datetime import datetime, timedelta, timezone
import asyncio
import httpx
from jose import jwt, JWTError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

ALGORITHM = "RS256" # Neon JWKS issues RS256 JWTs by default

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
    """Validate a token against Neon Auth JWKS and return the decoded payload."""
    jwks = await get_jwks_keys()
    
    try:
        # python-jose automatically finds the matching key by 'kid' in the header
        # and verifies the RSA signature of the RS256 token.
        payload = jwt.decode(
            token,
            jwks,
            algorithms=[ALGORITHM],
            options={"verify_aud": False} # Neon might not set 'aud' natively
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT Validation failed: {e}")
        return None
