"""W8: the login flow end to end over HTTP, against the migrated test database.

Covers the happy path (sign-up, sign-in, session, admin grant, sign-out),
wrong credentials, revoked access, expired and revoked sessions, and the
round-trip regressions fixed in W8 (no writes on session reads, one RLS
statement per transaction, single-round-trip pool ping).
"""
from __future__ import annotations

import re
import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import event, select

from app.core.security import create_access_token, get_password_hash
from app.db.session import async_session_maker, engine
from app.main import app
from app.models.plan import Plan
from app.models.user import User

GENERIC_401 = "Incorrect email or password"


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")


async def _sign_up(client, email: str, password: str) -> dict:
    response = await client.post("/api/auth/sign-up", json={"email": email, "password": password, "name": "W8 Test"})
    assert response.status_code == 200, response.text
    return response.json()


async def _platform_admin_and_plan(suffix: str):
    password = f"Adm-{suffix}-Pw1!"
    async with async_session_maker() as db:
        admin = User(
            id=f"adm_{suffix}",
            email=f"w8-adm-{suffix}@example.com",
            password_hash=get_password_hash(password),
            role="admin",
            is_platform_admin=True,
        )
        plan = Plan(id=f"plan_{suffix}", name="Granted", type="pay_as_you_go", feature_flags={"discover": True})
        db.add_all([admin, plan])
        await db.commit()
    return admin.email, password, plan.id


async def _token(client, email, password) -> str:
    response = await client.post("/api/auth/sign-in", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_happy_path_sign_up_sign_in_grant_session_and_sign_out():
    suffix = _suffix()
    email, password = f"w8-user-{suffix}@example.com", f"User-{suffix}-Pw1!"
    async with _client() as client:
        signed_up = await _sign_up(client, email, password)
        assert signed_up["access_status"] == "pending"
        assert not any(signed_up["feature_flags"].values())
        org_id = signed_up["org_id"]

        token = await _token(client, email.upper(), password)  # emails are case-insensitive
        session = await client.get("/api/auth/session", headers=_auth(token))
        assert session.status_code == 200
        assert session.json()["email"] == email and session.json()["access_status"] == "pending"

        admin_email, admin_password, plan_id = await _platform_admin_and_plan(suffix)
        admin_token = await _token(client, admin_email, admin_password)
        granted = await client.post(
            f"/api/admin/organizations/{org_id}/access-grant",
            json={"plan_id": plan_id, "feature_flags": {"discover": True}},
            headers=_auth(admin_token),
        )
        assert granted.status_code == 200, granted.text

        after_grant = (await client.get("/api/auth/session", headers=_auth(token))).json()
        assert after_grant["access_status"] == "approved"
        assert after_grant["feature_flags"].get("discover") is True

        signed_out = await client.post("/api/auth/sign-out", headers=_auth(token))
        assert signed_out.status_code == 200
        revoked = await client.get("/api/auth/session", headers=_auth(token))
        assert revoked.status_code == 401
        assert revoked.json()["detail"]["code"] == "session_revoked"

        # A fresh sign-in after sign-out works and is a different session.
        fresh = await _token(client, email, password)
        assert (await client.get("/api/auth/session", headers=_auth(fresh))).status_code == 200


@pytest.mark.asyncio
async def test_wrong_password_and_unknown_email_get_the_same_generic_401():
    suffix = _suffix()
    email, password = f"w8-wrong-{suffix}@example.com", f"Right-{suffix}-Pw1!"
    async with _client() as client:
        await _sign_up(client, email, password)
        wrong = await client.post("/api/auth/sign-in", json={"email": email, "password": password + "x"})
        unknown = await client.post("/api/auth/sign-in", json={"email": f"nobody-{suffix}@example.com", "password": password})
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["detail"] == unknown.json()["detail"] == GENERIC_401
        assert "access_token" not in wrong.json()


@pytest.mark.asyncio
async def test_revoked_access_turns_every_feature_off_without_ending_the_session():
    suffix = _suffix()
    email, password = f"w8-revoke-{suffix}@example.com", f"Rev-{suffix}-Pw1!"
    async with _client() as client:
        org_id = (await _sign_up(client, email, password))["org_id"]
        admin_email, admin_password, plan_id = await _platform_admin_and_plan(suffix)
        admin_token = await _token(client, admin_email, admin_password)
        await client.post(
            f"/api/admin/organizations/{org_id}/access-grant",
            json={"plan_id": plan_id, "feature_flags": {"discover": True}},
            headers=_auth(admin_token),
        )
        token = await _token(client, email, password)
        assert (await client.get("/api/auth/session", headers=_auth(token))).json()["access_status"] == "approved"

        revoked = await client.post(
            f"/api/admin/organizations/{org_id}/access-revoke", json={"note": "w8 test"}, headers=_auth(admin_token)
        )
        assert revoked.status_code == 200, revoked.text

        session = await client.get("/api/auth/session", headers=_auth(token))
        assert session.status_code == 200  # still signed in
        body = session.json()
        assert body["access_status"] != "approved"
        assert not any(body["feature_flags"].values())


@pytest.mark.asyncio
async def test_expired_and_forged_tokens_are_rejected():
    suffix = _suffix()
    email, password = f"w8-exp-{suffix}@example.com", f"Exp-{suffix}-Pw1!"
    async with _client() as client:
        user_id = (await _sign_up(client, email, password))["user_id"]
        expired = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-5))
        assert (await client.get("/api/auth/session", headers=_auth(expired))).status_code == 401
        valid = await _token(client, email, password)
        forged = valid[:-4] + ("AAAA" if not valid.endswith("AAAA") else "BBBB")
        assert (await client.get("/api/auth/session", headers=_auth(forged))).status_code == 401
        assert (await client.get("/api/auth/session")).status_code == 401


class _StatementLog:
    def __init__(self):
        self.statements: list[str] = []

    def __enter__(self):
        event.listen(engine.sync_engine, "before_cursor_execute", self._capture)
        return self

    def __exit__(self, *exc):
        event.remove(engine.sync_engine, "before_cursor_execute", self._capture)

    def _capture(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(re.sub(r"\s+", " ", statement).strip())


@pytest.mark.asyncio
async def test_session_read_issues_no_writes_and_one_rls_statement_per_application():
    suffix = _suffix()
    email, password = f"w8-rt-{suffix}@example.com", f"Rt-{suffix}-Pw1!"
    async with _client() as client:
        await _sign_up(client, email, password)
        token = await _token(client, email, password)
        # Make the daily counters stale so the old code would have flushed resets.
        async with async_session_maker() as db:
            from app.models.organization import Organization

            org = (await db.execute(select(Organization).where(Organization.name.like(f"w8-rt-{suffix}%")))).scalars().first()
            if org is not None:
                org.daily_credits_reset_at = None
                org.images_today_date = "2000-01-01"
                await db.commit()

        with _StatementLog() as log:
            response = await client.get("/api/auth/session", headers=_auth(token))
        assert response.status_code == 200
        writes = [s for s in log.statements if s.split(" ", 1)[0].upper() in ("UPDATE", "INSERT", "DELETE")]
        assert writes == [], writes
        rls = [s for s in log.statements if "set_config('helix.user_id'" in s]
        assert all("set_config('helix.enforce'" in s for s in rls), "RLS settings must be one statement"
        # get_db scope at begin, then user-only, then user+orgs: three distinct contexts.
        assert len(rls) == 3, log.statements
        assert len(log.statements) <= 10, log.statements


def test_tenant_listener_is_registered_once_for_the_shared_session_class():
    # Both makers share one Session class; a second install must be a no-op.
    # (The live count of one RLS statement per begin is asserted above.)
    from app.db import session as session_module

    sync_class = session_module.async_session_maker.class_.sync_session_class
    assert sync_class is session_module.worker_session_maker.class_.sync_session_class
    before = set(session_module._listened_session_classes)
    session_module._install_tenant_listener(session_module.async_session_maker)
    assert session_module._listened_session_classes == before == {sync_class}


def test_pool_ping_is_a_single_simple_query():
    from app.db.session import _single_round_trip_ping

    calls = []

    class FakeAsyncpg:
        async def execute(self, sql):
            calls.append(sql)
            return "SELECT 1"

    class FakeAdapted:
        _connection = FakeAsyncpg()

        @staticmethod
        def await_(awaitable):
            import asyncio

            return asyncio.run(awaitable)

        def _handle_exception(self, error):
            raise error

    assert _single_round_trip_ping(FakeAdapted()) is True
    assert calls == ["SELECT 1"]
