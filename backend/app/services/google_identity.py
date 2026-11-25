"""Verify a Google Sign-In ID token (no client secret needed).

The page gets an ID token from Google Identity Services and posts it here. We check the
signature against Google's published keys, then the audience (our client id), the issuer,
the expiry and `email_verified`. Nothing is trusted from the page except the token itself.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from jose import JWTError, jwt

from app.core.config import settings

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_KEYS_TTL_S = 3600
_keys: dict = {"at": 0.0, "jwks": None}
_lock = asyncio.Lock()


class GoogleTokenError(Exception):
    """The token is missing, malformed, expired, for another app or unverified."""


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: Optional[str]


async def _jwks(force: bool = False) -> dict:
    async with _lock:
        if not force and _keys["jwks"] and time.monotonic() - _keys["at"] < _KEYS_TTL_S:
            return _keys["jwks"]
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(CERTS_URL)
            res.raise_for_status()
        _keys.update(at=time.monotonic(), jwks=res.json())
        return _keys["jwks"]


def check_claims(claims: dict, client_id: str) -> GoogleIdentity:
    if claims.get("iss") not in ISSUERS:
        raise GoogleTokenError("wrong issuer")
    if claims.get("aud") != client_id:
        raise GoogleTokenError("wrong audience")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleTokenError("email not verified")
    sub, email = str(claims.get("sub") or ""), str(claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise GoogleTokenError("missing subject or email")
    name = str(claims.get("name") or "").strip() or None
    return GoogleIdentity(sub=sub, email=email, name=name)


async def verify_id_token(token: str) -> GoogleIdentity:
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleTokenError("google sign-in is not configured")
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        jwks = await _jwks()
        if kid not in {k.get("kid") for k in jwks.get("keys", [])}:
            jwks = await _jwks(force=True)  # Google rotated its keys
        claims = jwt.decode(
            token, jwks, algorithms=["RS256"], audience=client_id,
            options={"verify_iss": False, "verify_at_hash": False},
        )
    except (JWTError, httpx.HTTPError, ValueError) as exc:
        raise GoogleTokenError(type(exc).__name__) from None
    return check_claims(claims, client_id)
