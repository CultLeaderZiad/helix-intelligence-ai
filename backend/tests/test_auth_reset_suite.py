"""
Offline functional test for the password-reset flow plus the
case-insensitive email fixes. Uses an in-memory SQLite DB (aiosqlite), so
it needs no Postgres, network, or env credentials:

    cd backend
    ./venv/bin/python tests/test_auth_reset_suite.py
"""
import asyncio
import datetime
import importlib.util
import os
import sys
import types

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("USE_MOCKS", "False")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.models  # register every table on Base.metadata
from app.db.base import Base
from app.schemas.auth import UserLogin
from app.models.user import User
from app.core.security import get_password_hash, verify_password

# Load auth_service directly by file so the app.services package __init__
# (which imports app.db.session and needs asyncpg env) never runs.
_spec = importlib.util.spec_from_file_location(
    "auth_service_under_test", os.path.join(os.path.dirname(__file__), "..", "app", "services", "auth_service.py"))
auth_service = importlib.util.module_from_spec(_spec)
sys.modules["auth_service_under_test"] = auth_service
_spec.loader.exec_module(auth_service)

engine = create_async_engine("sqlite+aiosqlite://")
Session = async_sessionmaker(engine, expire_on_commit=False)


async def expect_http_error(coro, status_code: int):
    try:
        result = await coro
    except HTTPException as e:
        assert e.status_code == status_code, f"expected {status_code}, got {e.status_code}: {e.detail}"
        return e.detail
    raise AssertionError(f"expected HTTP {status_code} but no error was raised (returned {result!r})")


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # 1. Legacy account (created via the old Neon webhook) can never
        #    verify a password — it should still be recoverable via reset.
        legacy = User(
            id="usr_legacy",
            email="legacy@vynex.com",
            password_hash="EXTERNAL_AUTH_MANAGED",
            role="customer",
        )
        db.add(legacy)
        await db.commit()

        await expect_http_error(
            auth_service.authenticate_user(db, UserLogin(email="legacy@vynex.com", password="whatever")),
            401,
        )
        await expect_http_error(
            auth_service.authenticate_user(db, UserLogin(email="legacy@vynex.com", password="EXTERNAL_AUTH_MANAGED")),
            401,
        )
        print("[PASS] legacy/unverifiable hash still rejects sign-in with 401 (including EXTERNAL_AUTH_MANAGED)")

        # 2. Reset request mints a single-use token.
        user, raw_token = await auth_service.request_password_reset(db, "LEGACY@VYNEX.com")
        assert user.id == "usr_legacy", "reset lookup must be case-insensitive"
        assert raw_token
        print("[PASS] forgot-password mints a token (case-insensitive lookup)")

        # 3. Garbage tokens are rejected; a valid token resets once and is
        #    burned so the same link can never be reused.
        await expect_http_error(
            auth_service.reset_password(db, "not-a-real-token", "NewPass123!"), 400)
        user = await auth_service.reset_password(db, raw_token, "NewPass123!")
        assert user.password_reset_token_hash is None
        assert await verify_password("NewPass123!", user.password_hash)
        await expect_http_error(
            auth_service.reset_password(db, raw_token, "AnotherPass123!"), 400)
        print("[PASS] invalid token rejected; valid token single-use")

        # 4. A fresh token works and signs the account in afterwards.
        _, token2 = await auth_service.request_password_reset(db, "legacy@vynex.com")
        user = await auth_service.reset_password(db, token2, "NewPass1234!")
        assert await verify_password("NewPass1234!", user.password_hash)
        print("[PASS] a second reset request also works")

        # 5. Sign-in works with the new password and is case-insensitive.
        token = await auth_service.authenticate_user(
            db, UserLogin(email="LEGACY@vynex.com", password="NewPass1234!"))
        assert token
        await expect_http_error(
            auth_service.authenticate_user(db, UserLogin(email="legacy@vynex.com", password="OldPass")), 401)
        print("[PASS] sign-in with new password; case-insensitive email; wrong password 401")

        # 6. Sign-up normalizes emails and rejects duplicate case variants.
        new_user_req = types.SimpleNamespace(email="Mixed.Case@Test.com", password="Passw0rd!", name="Mixed")
        registered = await auth_service.register_user(db, new_user_req)
        assert registered.email == "mixed.case@test.com", registered.email
        await expect_http_error(
            auth_service.register_user(db, types.SimpleNamespace(email="MIXED.CASE@test.COM", password="Passw0rd!", name="Dup")),
            400,
        )
        print("[PASS] sign-up stores lowercase email; duplicate rejected case-insensitively")

        # 7. Stale links do NOT invalidate newer links (F18)
        _, link_stale = await auth_service.request_password_reset(db, "legacy@vynex.com")
        _, link_fresh = await auth_service.request_password_reset(db, "legacy@vynex.com")
        # Submitting the stale link must fail with 400
        await expect_http_error(
            auth_service.reset_password(db, link_stale, "StaleAttempt123!"), 400)
        # But the fresh link must STILL succeed!
        user_after_fresh = await auth_service.reset_password(db, link_fresh, "FreshSuccess123!")
        assert await verify_password("FreshSuccess123!", user_after_fresh.password_hash)
        print("[PASS] F18: stale reset link does not invalidate new link; new link succeeds")

        # 8. Session revocation on password reset or logout (F19)
        from app.core.deps import get_current_user
        session_token_1 = await auth_service.authenticate_user(
            db, UserLogin(email="legacy@vynex.com", password="FreshSuccess123!"))
        # First verification works
        auth_u1 = await get_current_user(db=db, token=session_token_1)
        assert auth_u1.id == "usr_legacy"
        
        # Now revoke sessions
        await auth_service.revoke_user_sessions(db, auth_u1)
        # Old token is now revoked and rejected with 401
        await expect_http_error(
            get_current_user(db=db, token=session_token_1), 401)
        print("[PASS] F19: old token is revoked and rejected with 401 after session revocation")

    print("\nALL AUTH RESET TESTS PASSED")


def test_auth_reset_suite():
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
