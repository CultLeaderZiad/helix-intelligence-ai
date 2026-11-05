"""Focused W0 behavior tests. Synthetic identities only; no production data."""

from __future__ import annotations

import base64
import io
import json
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwt
from PIL import Image

from app.core.config import settings, validate_boot_invariants
from app.core.deps import authenticate_bearer, session_is_revoked
from app.core.security import create_access_token, verify_session_token
from app.middleware.rate_limit import client_ip
from app.models.organization import Organization
from app.models.pattern import Pattern
from app.models.playbook import Playbook
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services.avatar_image import AvatarRejected, prepare_avatar_image
from app.services.creative_service import list_patterns
from app.services.playbook_service import get_public_playbook
from app.services.safe_fetch import (
    PublicDestination,
    UnsafeFetch,
    _PinningTransport,
    decode_image_data_url,
    safe_http_get,
)
from app.services.security_service import decrypt_secret, encrypt_secret, safe_decrypt_secret


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(host: str, headers: dict):
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers)


def test_ssrf_blocks_redirect_to_loopback():
    def resolve(hostname, port):
        if hostname == "example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
        raise socket.gaierror(hostname)

    class Redirect:
        is_redirect = True
        headers = {"location": "http://127.0.0.1/latest/meta-data/"}
        content = b""

    with patch("app.services.safe_fetch._resolve", resolve), patch("httpx.get", return_value=Redirect()) as fetched:
        with pytest.raises(ValueError, match="SSRF blocked"):
            safe_http_get("https://example.com/start")
    assert fetched.call_count == 1


def test_ssrf_blocks_dns_that_resolves_to_loopback_before_connect():
    def resolve(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    with patch("app.services.safe_fetch._resolve", resolve), patch("httpx.get") as fetched:
        with pytest.raises(UnsafeFetch, match="SSRF blocked"):
            safe_http_get("https://rebind.example/secret")
    fetched.assert_not_called()


def test_pinning_transport_connects_to_validated_address():
    seen = {}

    class Capture:
        def handle_request(self, request):
            seen["host"] = request.url.host
            seen["sni"] = request.extensions.get("sni_hostname")
            seen["header"] = request.headers.get("host")
            import httpx
            return httpx.Response(200, content=b"ok")

        def close(self):
            return None

    destination = PublicDestination(
        url="https://example.com/a",
        scheme="https",
        hostname="example.com",
        port=443,
        ip="93.184.216.34",
    )
    transport = _PinningTransport(destination)
    transport._inner = Capture()
    import httpx
    transport.handle_request(httpx.Request("GET", destination.url))
    assert seen["host"] == "93.184.216.34"
    assert seen["sni"] == "example.com"
    assert seen["header"] == "example.com"


def test_inline_image_rejects_oversized_payload_before_decode():
    with pytest.raises(UnsafeFetch, match="exceeds"):
        decode_image_data_url("data:image/png;base64," + ("A" * 80), max_bytes=8)


def test_avatar_rejects_svg_html_and_oversize_and_reencodes_png():
    with pytest.raises(AvatarRejected):
        prepare_avatar_image(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    with pytest.raises(AvatarRejected):
        prepare_avatar_image(b"<html><script>alert(1)</script></html>")
    with pytest.raises(AvatarRejected):
        prepare_avatar_image(_png_bytes() + b"\x00" * 10, max_bytes=8)
    encoded, mime, ext = prepare_avatar_image(_png_bytes())
    assert mime == "image/png"
    assert ext == "png"
    assert b"<svg" not in encoded.lower()
    with Image.open(io.BytesIO(encoded)) as image:
        assert image.format == "PNG"


@pytest.mark.asyncio
async def test_versionless_local_token_is_rejected_and_revocation_boundary_holds():
    versionless = jwt.encode(
        {"sub": "user-1", "iat": int(time.time()), "exp": int(time.time()) + 600},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    assert await verify_session_token(versionless) is None

    current = create_access_token("user-1", token_version=2)
    payload = await verify_session_token(current)
    assert payload["ver"] == 2
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE

    revoked_user = SimpleNamespace(signup_metadata={
        "token_version": 3,
        "sessions_revoked_at": "2020-01-01T00:00:00+00:00",
    })
    assert session_is_revoked(revoked_user, {"_token_class": "local", "ver": 2, "iat": int(time.time())})
    assert session_is_revoked(revoked_user, {"_token_class": "local", "ver": None, "iat": int(time.time()) + 10})


@pytest.mark.asyncio
async def test_externally_signed_tokens_are_rejected():
    """Only Helix HS256 session tokens are accepted (W8 removed Neon Auth)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    now = int(time.time())
    claims = {"sub": "user-1", "iat": now, "exp": now + 600, "ver": 1,
              "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE}
    rs256 = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "kid-1"})
    assert await verify_session_token(rs256) is None
    assert await verify_session_token("not-a-jwt") is None
    assert await verify_session_token("") is None


@pytest.mark.asyncio
async def test_banned_local_session_is_forbidden():
    token = create_access_token("banned-user", token_version=1)
    user = SimpleNamespace(
        id="banned-user",
        is_banned=True,
        is_suspended=False,
        signup_metadata={"token_version": 1},
    )

    class DB:
        async def execute(self, _stmt):
            return SimpleNamespace(scalar_one_or_none=lambda: user)

    with pytest.raises(HTTPException) as exc:
        await authenticate_bearer(DB(), token)
    assert exc.value.status_code == 403


def test_spoofed_forwarded_for_is_ignored_unless_peer_is_trusted():
    spoofed = _request("203.0.113.10", {
        "x-forwarded-for": "1.2.3.4",
        "cf-connecting-ip": "8.8.8.8",
    })
    assert client_ip(spoofed) == "203.0.113.10"
    with patch.object(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8"):
        trusted = _request("10.1.2.3", {"x-forwarded-for": "1.2.3.4, 198.51.100.20"})
        assert client_ip(trusted) == "198.51.100.20"


def test_impersonation_token_is_short_lived_and_carries_actor_scope():
    token = create_access_token(
        "target-user",
        role="customer",
        token_version=4,
        expires_delta=timedelta(minutes=settings.IMPERSONATION_TOKEN_EXPIRE_MINUTES),
        extra_claims={"token_use": "impersonation", "scope": "impersonation", "act": "actor-1"},
    )
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )
    assert payload["sub"] == "target-user"
    assert payload["ver"] == 4
    assert payload["token_use"] == "impersonation"
    assert payload["scope"] == "impersonation"
    assert payload["act"] == "actor-1"
    assert payload["exp"] - payload["iat"] <= settings.IMPERSONATION_TOKEN_EXPIRE_MINUTES * 60


@pytest.mark.asyncio
async def test_production_reset_flag_is_forbidden_and_response_has_no_link():
    class Cfg:
        ENVIRONMENT = "production"
        AUTH_DEV_RESET_RETURN = True
        SECRET_KEY = "x" * 40
        CREDENTIAL_ENCRYPTION_KEY = "y" * 40
        RESEND_API_KEY = "re_test"
        RESEND_FROM = "alerts@example.com"
        PUBLIC_APP_BASE_URL = "https://app.example.com"
        APIFY_ENABLED = False
        APIFY_API_TOKEN = ""
        GROQ_MODEL = "llama"
        GEMINI_TEXT_MODEL = "gemini"
        GEMINI_IMAGE_MODEL = "gemini-image"

    with pytest.raises(RuntimeError, match="AUTH_DEV_RESET_RETURN"):
        validate_boot_invariants(Cfg())

    from app.api.routers.auth import forgot_password
    from app.schemas.auth import PasswordResetRequest

    class Empty:
        def scalar_one_or_none(self):
            return None

    class DB:
        async def execute(self, _stmt):
            return Empty()

    with patch.object(settings, "ENVIRONMENT", "production"), patch.object(settings, "AUTH_DEV_RESET_RETURN", True):
        response = await forgot_password(PasswordResetRequest(email="nobody-w0@example.com"), DB())
    assert response == {"ok": True}
    assert "reset_url" not in response


def test_encryption_key_is_versioned_and_plaintext_is_not_returned():
    token = encrypt_secret("byok-secret-value")
    assert token.startswith("v")
    assert "byok-secret-value" not in token
    assert decrypt_secret(token) == "byok-secret-value"
    assert safe_decrypt_secret("plaintext-key") == ""




@pytest.mark.asyncio
async def test_two_tenants_cannot_read_null_job_patterns_or_anonymous_playbooks():
    from app.db.session import worker_session_maker

    suffix = uuid.uuid4().hex[:8]
    async with worker_session_maker() as db:
        user_a = User(id=f"usr_a_{suffix}", email=f"a_{suffix}@example.com", password_hash="x", role="admin")
        user_b = User(id=f"usr_b_{suffix}", email=f"b_{suffix}@example.com", password_hash="x", role="customer")
        db.add_all([user_a, user_b])
        await db.flush()
        org_a = Organization(id=f"org_a_{suffix}", name="A", owner_id=user_a.id, plan_id="plan_trial_default", plan="trial")
        org_b = Organization(id=f"org_b_{suffix}", name="B", owner_id=user_b.id, plan_id="plan_trial_default", plan="trial")
        db.add_all([org_a, org_b])
        await db.flush()
        job_a = ScrapeJob(id=f"job_a_{suffix}", org_id=org_a.id, query="private", status="succeeded")
        db.add(job_a)
        await db.flush()
        owned = Pattern(id=f"pat_owned_{suffix}", job_id=job_a.id, label="owned", family="copy", prevalence=0.2, lift_index=1.1)
        unowned = Pattern(id=f"pat_null_{suffix}", job_id=None, label="NULLJOB-CANARY", family="copy", prevalence=0.9, lift_index=2.0)
        db.add_all([owned, unowned])
        playbook = Playbook(
            id=f"pb_{suffix}",
            public_id=f"pub_{suffix}",
            user_id=user_a.id,
            org_id=org_a.id,
            brand_name="Canary",
            query="private",
            title="Private report",
            summary="canary",
            patterns=[{"name": "NULLJOB-CANARY"}],
            creatives=[],
            insights=[],
        )
        db.add(playbook)
        await db.commit()

        listed = await list_patterns(db, user_org_ids=[org_b.id])
        assert all(item.label != "NULLJOB-CANARY" for item in listed.items)
        assert all(item.id != owned.id for item in listed.items)
        own_list = await list_patterns(db, user_org_ids=[org_a.id])
        assert any(item.id == owned.id for item in own_list.items)
        assert all(item.label != "NULLJOB-CANARY" for item in own_list.items)


        with pytest.raises(HTTPException) as anon:
            await get_public_playbook(db, playbook.public_id, None)
        assert anon.value.status_code == 401
        with pytest.raises(HTTPException) as foreign:
            await get_public_playbook(db, playbook.public_id, user_b)
        assert foreign.value.status_code == 404

        from app.core.deps import get_current_user
        with pytest.raises(HTTPException) as missing:
            await get_current_user(db=db, token=None, x_api_key=None)
        assert missing.value.status_code == 401
