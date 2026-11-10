"""W8: repeated wrong passwords lock the account, not just one client IP."""
from __future__ import annotations

import types
import uuid

import httpx
import pytest

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import async_session_maker
from app.main import app
from app.middleware import rate_limit
from app.models.user import User
from app.services import auth_service

LIMIT = 3


@pytest.fixture(autouse=True)
def _small_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "SIGN_IN_FAILURE_LIMIT", LIMIT)
    monkeypatch.setattr(settings, "SIGN_IN_FAILURE_WINDOW_S", 900)
    monkeypatch.setattr(settings, "SIGN_IN_LOCK_S", 900)
    auth_service._UNKNOWN_FAILURES.clear()
    yield
    auth_service._UNKNOWN_FAILURES.clear()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")


def _request(peer: str, headers: dict) -> types.SimpleNamespace:
    return types.SimpleNamespace(client=types.SimpleNamespace(host=peer), headers=headers)


def test_unknown_emails_lock_on_the_same_attempt_as_real_accounts():
    email = f"nobody-{uuid.uuid4().hex[:8]}@example.com"
    results = [auth_service._unknown_email_failure(email) for _ in range(LIMIT)]
    assert results == [False] * (LIMIT - 1) + [True]
    assert auth_service._unknown_email_throttled(email)


def test_untrusted_private_proxy_is_reported(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "")
    monkeypatch.setattr(rate_limit, "_proxy_warning_logged", False)
    behind_proxy = _request("10.1.2.3", {"x-forwarded-for": "203.0.113.9"})
    assert rate_limit.warn_if_untrusted_proxy(behind_proxy) is True
    assert rate_limit.client_ip(behind_proxy) == "10.1.2.3"

    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    assert rate_limit.warn_if_untrusted_proxy(behind_proxy) is False
    assert rate_limit.client_ip(behind_proxy) == "203.0.113.9"
    # A public peer is the client itself, not a hosting proxy.
    assert rate_limit.warn_if_untrusted_proxy(_request("8.8.8.8", {"x-forwarded-for": "1.2.3.4"})) is False


async def _account(password: str) -> str:
    s = uuid.uuid4().hex[:10]
    email = f"w8-lock-{s}@example.com"
    async with async_session_maker() as db:
        db.add(User(id=f"lock_{s}", email=email, password_hash=get_password_hash(password), role="customer"))
        await db.commit()
    return email


@pytest.mark.asyncio
async def test_wrong_passwords_lock_the_account_even_for_the_right_password():
    password = f"Right-{uuid.uuid4().hex[:6]}-Pw1!"
    email = await _account(password)
    async with _client() as client:
        codes = [
            (await client.post("/api/auth/sign-in", json={"email": email, "password": "wrong-password-1"})).status_code
            for _ in range(LIMIT)
        ]
        assert codes == [401] * (LIMIT - 1) + [429]
        locked = await client.post("/api/auth/sign-in", json={"email": email, "password": password})
        assert locked.status_code == 429
        assert locked.json()["detail"]["code"] == "too_many_sign_in_attempts"
        assert int(locked.headers["retry-after"]) > 0

        unknown = f"w8-none-{uuid.uuid4().hex[:8]}@example.com"
        unknown_codes = [
            (await client.post("/api/auth/sign-in", json={"email": unknown, "password": "wrong-password-1"})).status_code
            for _ in range(LIMIT + 1)
        ]
        assert unknown_codes == [401] * (LIMIT - 1) + [429, 429]


@pytest.mark.asyncio
async def test_success_clears_failures_and_a_reset_ends_the_lock():
    password = f"Right-{uuid.uuid4().hex[:6]}-Pw1!"
    email = await _account(password)
    async with _client() as client:
        for _ in range(LIMIT - 1):
            assert (await client.post("/api/auth/sign-in", json={"email": email, "password": "nope-nope-1"})).status_code == 401
        assert (await client.post("/api/auth/sign-in", json={"email": email, "password": password})).status_code == 200
        # The counter restarted, so the next wrong password is not the last straw.
        assert (await client.post("/api/auth/sign-in", json={"email": email, "password": "nope-nope-1"})).status_code == 401

        for _ in range(LIMIT):
            await client.post("/api/auth/sign-in", json={"email": email, "password": "nope-nope-1"})
        assert (await client.post("/api/auth/sign-in", json={"email": email, "password": password})).status_code == 429

    async with async_session_maker() as db:
        _user, raw_token = await auth_service.request_password_reset(db, email)
        new_password = password + "x"
        await auth_service.reset_password(db, raw_token, new_password)
    async with _client() as client:
        assert (await client.post("/api/auth/sign-in", json={"email": email, "password": new_password})).status_code == 200
