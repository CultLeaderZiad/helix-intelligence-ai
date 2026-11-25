"""Google sign-in: ID token checks run against a locally signed token, no network."""
from __future__ import annotations

import asyncio
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.core.config import settings
from app.services import google_identity as g

CLIENT = "123-abc.apps.googleusercontent.com"


@pytest.fixture()
def signer(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub = jwk.construct(key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo), "RS256").to_dict()
    pub["kid"] = "k1"

    async def fake_jwks(force=False):
        return {"keys": [pub]}

    monkeypatch.setattr(g, "_jwks", fake_jwks)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", CLIENT)

    def sign(**over):
        claims = {"iss": "https://accounts.google.com", "aud": CLIENT, "sub": "g-1", "email": "A@Example.com",
                  "email_verified": True, "name": "Ana", "exp": int(time.time()) + 600}
        claims.update(over)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, pem.decode(), algorithm="RS256", headers={"kid": "k1"})

    return sign


def verify(token):
    return asyncio.run(g.verify_id_token(token))


def test_valid_token_gives_a_lowercased_identity(signer):
    ident = verify(signer())
    assert (ident.sub, ident.email, ident.name) == ("g-1", "a@example.com", "Ana")


@pytest.mark.parametrize("over", [
    {"aud": "someone-else.apps.googleusercontent.com"},
    {"iss": "https://evil.example"},
    {"email_verified": False},
    {"exp": int(time.time()) - 10},
    {"sub": None},
    {"email": None},
])
def test_bad_tokens_are_refused(signer, over):
    with pytest.raises(g.GoogleTokenError):
        verify(signer(**over))


def test_token_signed_by_another_key_is_refused(signer):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    forged = jwt.encode({"iss": "accounts.google.com", "aud": CLIENT, "sub": "x", "email": "v@example.com",
                         "email_verified": True, "exp": int(time.time()) + 600}, pem.decode(),
                        algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(g.GoogleTokenError):
        verify(forged)


def test_garbage_and_disabled_feature_are_refused(signer, monkeypatch):
    with pytest.raises(g.GoogleTokenError):
        verify("not-a-token")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    with pytest.raises(g.GoogleTokenError):
        verify(signer())


def test_unknown_key_ids_cannot_make_us_call_google_more_than_once_a_minute(monkeypatch):
    calls = []

    class Res:
        def raise_for_status(self):
            pass

        def json(self):
            return {"keys": [{"kid": "k"}]}

    class Client:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url):
            calls.append(url)
            return Res()

    monkeypatch.setattr(g.httpx, "AsyncClient", Client)
    monkeypatch.setitem(g._keys, "jwks", None)
    monkeypatch.setitem(g._keys, "at", 0.0)

    async def many():
        for _ in range(5):
            await g._jwks(force=True)

    asyncio.run(many())
    assert len(calls) == 1
