"""
Auth & Security Test Suite

Covers the authentication and secrets paths with no network and no database:
  - get_password_hash / verify_password (PBKDF2 contract, malformed hashes)
  - create_access_token / verify_neon_token (local HS256, expired/garbage rejection,
    Neon JWKS RS256 fallback via mocked JWKS fetch)
  - api_key_service (hash determinism, valid/invalid API key authentication)
  - provider_resolver BYOK branches: decryption failure -> 400, missing credential
    fallback to managed, trial always managed
"""
import asyncio
import base64
import datetime
import os
import sys
from unittest import mock

os.environ.setdefault("SECRET_KEY", "helix-test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.models.user import User
from app.models.organization import Organization
from app.models.api_key import ApiKey
from app.models.workspace_credential import WorkspaceProviderCredential
from app.core import security as core_security
from app.services import api_key_service
from app.services import provider_resolver
from app.services.ai.pollinations_provider import PollinationsProvider


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows if isinstance(rows, list) else [rows]

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Routes SQLAlchemy statements by their target entity to queued rows."""

    def __init__(self):
        self.results = {}
        self.executed = []
        self.committed = 0

    def queue(self, entity, rows):
        self.results.setdefault(entity.__name__, []).extend(rows)

    def _rows_for(self, stmt):
        try:
            descriptions = stmt.column_descriptions
        except Exception:
            return None
        for d in descriptions:
            entity = d.get("entity")
            if entity is not None and entity.__name__ in self.results and self.results[entity.__name__]:
                return self.results[entity.__name__].pop(0)
        return None

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _FakeResult(self._rows_for(stmt) or [])

    def add(self, obj):
        pass

    async def commit(self):
        self.committed += 1

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def make_user(**overrides):
    defaults = dict(
        id="u_1",
        email="user@helix.ai",
        password_hash="x",
        role="customer",
        trial_expires_at=utc_now() - datetime.timedelta(days=10),
    )
    defaults.update(overrides)
    return User(**defaults)


def make_org(**overrides):
    defaults = dict(
        id="org_1",
        name="Workspace",
        owner_id="u_1",
        plan_id="plan_growth_50",
        plan="growth",
        credit_balance=100.0,
        status="active",
    )
    defaults.update(overrides)
    return Organization(**defaults)


async def _auth_fail(secret=None):
    raise ValueError("Authentication service unavailable")


# ---------------------------------------------------------------------------
# Password hashing / verification
# ---------------------------------------------------------------------------

def test_password_hash_roundtrip():
    hashed = core_security.get_password_hash("s3cret-password!")
    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert asyncio.run(core_security.verify_password("s3cret-password!", hashed)) is True
    assert asyncio.run(core_security.verify_password("wrong-password", hashed)) is False
    print("[PASS] test_password_hash_roundtrip passed")


def test_password_hash_salts_are_unique():
    assert core_security.get_password_hash("same-password") != core_security.get_password_hash("same-password")
    print("[PASS] test_password_hash_salts_are_unique passed")


def test_verify_password_rejects_malformed_hashes():
    assert asyncio.run(core_security.verify_password("anything", "pbkdf2:sha256:100000$onlysalt")) is False
    assert asyncio.run(core_security.verify_password("anything", "")) is False
    assert asyncio.run(core_security.verify_password("", "pbkdf2:sha256:100000$salt$key")) is False
    assert asyncio.run(core_security.verify_password("anything", "not-a-valid-hash-format")) is False
    print("[PASS] test_verify_password_rejects_malformed_hashes passed")


# ---------------------------------------------------------------------------
# JWT creation / verification
# ---------------------------------------------------------------------------

def test_access_token_roundtrip_locally_signed():
    token = core_security.create_access_token("u_abc", role="customer")
    payload = asyncio.run(core_security.verify_neon_token(token))
    assert payload is not None
    assert payload["sub"] == "u_abc"
    assert payload["role"] == "customer"
    print("[PASS] test_access_token_roundtrip_locally_signed passed")


def test_verify_neon_token_rejects_garbage():
    with mock.patch.object(core_security, "get_jwks_keys", _auth_fail):
        assert asyncio.run(core_security.verify_neon_token("not-a-jwt")) is None
    print("[PASS] test_verify_neon_token_rejects_garbage passed")


def test_verify_neon_token_rejects_expired():
    token = core_security.create_access_token("u_abc", expires_delta=datetime.timedelta(seconds=-30))
    with mock.patch.object(core_security, "get_jwks_keys", _auth_fail):
        assert asyncio.run(core_security.verify_neon_token(token)) is None
    print("[PASS] test_verify_neon_token_rejects_expired passed")


def _rsa_jwks():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private_key.public_key().public_numbers()

    def b64u_int(value):
        length = (value.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()

    jwks = {
        "keys": [{
            "kty": "RSA",
            "kid": "test-kid-1",
            "use": "sig",
            "alg": "RS256",
            "n": b64u_int(public.n),
            "e": b64u_int(public.e),
        }]
    }
    return private_key, jwks


def test_verify_neon_token_accepts_neon_rs256_jwks():
    private_key, jwks = _rsa_jwks()
    token = jose_jwt.encode(
        {"sub": "neon-user-42", "role": "customer", "exp": utc_now() + datetime.timedelta(hours=1)},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-kid-1"},
    )
    async def fake_jwks_fetch():
        return jwks

    with mock.patch.object(core_security, "get_jwks_keys", fake_jwks_fetch):
        payload = asyncio.run(core_security.verify_neon_token(token))
    assert payload is not None
    assert payload["sub"] == "neon-user-42"
    print("[PASS] test_verify_neon_token_accepts_neon_rs256_jwks passed")


# ---------------------------------------------------------------------------
# API key service
# ---------------------------------------------------------------------------

def test_hash_key_is_deterministic_sha256():
    first = api_key_service.hash_key("hlx_live_abc123")
    second = api_key_service.hash_key("hlx_live_abc123")
    assert first == second
    assert first != api_key_service.hash_key("hlx_live_abc124")
    assert len(first) == 64
    print("[PASS] test_hash_key_is_deterministic_sha256 passed")


def test_authenticate_api_key_valid_key_returns_user_and_org():
    user = make_user()
    org = make_org()
    api_key = ApiKey(
        id="key_1",
        org_id=org.id,
        user_id=user.id,
        name="Test Key",
        key_hash=api_key_service.hash_key("hlx_live_valid"),
        prefix="hlx_live_",
        is_active=True,
    )
    db = FakeSession()
    db.queue(ApiKey, [(api_key, user, org)])
    returned_user, returned_org = asyncio.run(api_key_service.authenticate_api_key(db, "hlx_live_valid"))
    assert returned_user is user
    assert returned_org is org
    assert api_key.last_used_at is not None
    assert db.committed >= 1
    print("[PASS] test_authenticate_api_key_valid_key_returns_user_and_org passed")


def test_authenticate_api_key_invalid_key_raises_401():
    db = FakeSession()
    try:
        asyncio.run(api_key_service.authenticate_api_key(db, "hlx_live_unknown"))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Invalid or revoked API Key" in str(exc.detail)
    print("[PASS] test_authenticate_api_key_invalid_key_raises_401 passed")


# ---------------------------------------------------------------------------
# Provider resolution (BYOK / managed routing)
# ---------------------------------------------------------------------------

def test_resolve_image_provider_trial_always_managed():
    user = make_user(trial_expires_at=utc_now() + datetime.timedelta(days=5))
    org = make_org(plan="trial", plan_id="plan_trial_default")
    db = FakeSession()
    provider, mode = asyncio.run(provider_resolver.resolve_image_provider(db, user, org))
    assert mode == "managed"
    assert isinstance(provider, PollinationsProvider)
    print("[PASS] test_resolve_image_provider_trial_always_managed passed")


def test_resolve_image_provider_paid_without_credential_falls_back_to_managed():
    db = FakeSession()
    provider, mode = asyncio.run(provider_resolver.resolve_image_provider(db, make_user(), make_org()))
    assert mode == "managed"
    assert isinstance(provider, PollinationsProvider)
    print("[PASS] test_resolve_image_provider_paid_without_credential_falls_back_to_managed passed")


def test_resolve_image_provider_byok_decryption_failure_raises_400():
    credential = WorkspaceProviderCredential(
        id="cred_1",
        org_id="org_1",
        provider="google_gemini",
        encrypted_secret="corrupted-not-a-fernet-token",
        credential_mode="byok",
    )
    db = FakeSession()
    db.queue(WorkspaceProviderCredential, [credential])
    try:
        asyncio.run(provider_resolver.resolve_image_provider(db, make_user(), make_org()))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["code"] == "byok_decryption_failed"
    print("[PASS] test_resolve_image_provider_byok_decryption_failure_raises_400 passed")


def test_resolve_image_provider_managed_credential_is_ignored():
    # A credential stored in 'managed' mode must not be treated as BYOK.
    credential = WorkspaceProviderCredential(
        id="cred_2",
        org_id="org_1",
        provider="google_gemini",
        encrypted_secret="irrelevant",
        credential_mode="managed",
    )
    db = FakeSession()
    db.queue(WorkspaceProviderCredential, [credential])
    provider, mode = asyncio.run(provider_resolver.resolve_image_provider(db, make_user(), make_org()))
    assert mode == "managed"
    assert isinstance(provider, PollinationsProvider)
    print("[PASS] test_resolve_image_provider_managed_credential_is_ignored passed")


if __name__ == "__main__":
    print("Running Auth & Security Test Suite...")
    test_password_hash_roundtrip()
    test_password_hash_salts_are_unique()
    test_verify_password_rejects_malformed_hashes()
    test_access_token_roundtrip_locally_signed()
    test_verify_neon_token_rejects_garbage()
    test_verify_neon_token_rejects_expired()
    test_verify_neon_token_accepts_neon_rs256_jwks()
    test_hash_key_is_deterministic_sha256()
    test_authenticate_api_key_valid_key_returns_user_and_org()
    test_authenticate_api_key_invalid_key_raises_401()
    test_resolve_image_provider_trial_always_managed()
    test_resolve_image_provider_paid_without_credential_falls_back_to_managed()
    test_resolve_image_provider_byok_decryption_failure_raises_400()
    test_resolve_image_provider_managed_credential_is_ignored()
    print("\n=======================================================")
    print("ALL 14 AUTH & SECURITY SUITE TESTS PASSED (100% SUCCESS)")
    print("=======================================================")
