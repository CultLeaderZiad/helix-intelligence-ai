"""W8: the users and api_keys tables are no longer readable across tenants.

Run as the restricted ``helix_app`` role (SET LOCAL ROLE), the way the API
connects in production. The CI database user is a superuser and bypasses RLS,
so app-level tests alone would not catch a missing scope.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.tenancy import TenantContext, tenant_settings_params
from app.db.session import async_session_maker, engine
from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User


def test_the_email_lookup_scope_is_sent_lower_case():
    params = tenant_settings_params(TenantContext([], "", auth_email="X@Example.COM".lower()))
    assert params["auth_email"] == "x@example.com"
    assert tenant_settings_params(TenantContext(["o1"], "u1"))["auth_email"] == ""


async def _fixture(s: str) -> dict:
    ids = {k: f"rls{k}_{s}" for k in ("a", "b", "m", "oa", "ob")}
    async with async_session_maker() as db:
        db.add_all([
            User(id=ids["a"], email=f"rls-a-{s}@example.com", password_hash="x", role="customer"),
            User(id=ids["b"], email=f"rls-b-{s}@example.com", password_hash="x", role="customer"),
            User(id=ids["m"], email=f"rls-m-{s}@example.com", password_hash="x", role="customer"),
        ])
        await db.flush()
        db.add_all([
            Organization(id=ids["oa"], name="A", owner_id=ids["a"], plan="trial"),
            Organization(id=ids["ob"], name="B", owner_id=ids["b"], plan="trial"),
        ])
        await db.flush()
        db.add(OrganizationMember(org_id=ids["oa"], user_id=ids["m"], role="member"))
        db.add_all([
            ApiKey(org_id=ids["oa"], user_id=ids["a"], key_hash=f"ha_{s}", prefix="hlx_a"),
            ApiKey(org_id=ids["ob"], user_id=ids["b"], key_hash=f"hb_{s}", prefix="hlx_b"),
        ])
        await db.commit()
    return ids


async def _visible(conn, ids, *, user_id="", org_ids="", admin="0", auth_email=""):
    async with conn.begin():
        await conn.execute(text("SET LOCAL ROLE helix_app"))
        await conn.execute(
            text(
                "SELECT set_config('helix.user_id', :u, true), set_config('helix.org_ids', :o, true), "
                "set_config('helix.platform_admin', :a, true), set_config('helix.enforce', '1', true), "
                "set_config('helix.auth_email', :e, true)"
            ),
            {"u": user_id, "o": org_ids, "a": admin, "e": auth_email},
        )
        rows = await conn.execute(
            text("SELECT id FROM users WHERE id = ANY(:ids)"), {"ids": [ids["a"], ids["b"], ids["m"]]}
        )
        users = sorted(r[0] for r in rows)
        keys = (await conn.execute(
            text("SELECT org_id FROM api_keys WHERE org_id = ANY(:o)"), {"o": [ids["oa"], ids["ob"]]}
        )).scalars().all()
        await conn.execute(text("RESET ROLE"))
    return users, sorted(keys)


@pytest.mark.asyncio
async def test_users_and_api_keys_follow_the_caller_scope():
    s = uuid.uuid4().hex[:8]
    ids = await _fixture(s)
    async with engine.connect() as conn:
        assert await _visible(conn, ids) == ([], [])
        assert await _visible(conn, ids, user_id=ids["a"]) == ([ids["a"]], [])
        assert await _visible(conn, ids, user_id=ids["a"], org_ids=ids["oa"]) == (
            sorted([ids["a"], ids["m"]]), [ids["oa"]]
        )
        assert await _visible(conn, ids, auth_email=f"rls-b-{s}@example.com") == ([ids["b"]], [])
        assert await _visible(conn, ids, admin="1") == (
            sorted([ids["a"], ids["b"], ids["m"]]), sorted([ids["oa"], ids["ob"]])
        )


@pytest.mark.asyncio
async def test_restricted_role_cannot_write_other_users_or_create_a_mismatched_account():
    s = uuid.uuid4().hex[:8]
    ids = await _fixture(s)
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text("SET LOCAL ROLE helix_app"))
            await conn.execute(text(
                "SELECT set_config('helix.user_id', :u, true), set_config('helix.org_ids', :o, true)"
            ), {"u": ids["a"], "o": ids["oa"]})
            # B is outside the scope: the update finds no row.
            outside = await conn.execute(text("UPDATE users SET full_name = 'x' WHERE id = :b"), {"b": ids["b"]})
            assert outside.rowcount == 0
            own = await conn.execute(text("UPDATE users SET full_name = 'me' WHERE id = :a"), {"a": ids["a"]})
            assert own.rowcount == 1

        # M is readable as a teammate but not writable: the update is refused.
        with pytest.raises(Exception) as teammate:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE helix_app"))
                await conn.execute(text(
                    "SELECT set_config('helix.user_id', :u, true), set_config('helix.org_ids', :o, true)"
                ), {"u": ids["a"], "o": ids["oa"]})
                await conn.execute(text("UPDATE users SET full_name = 'x' WHERE id = :m"), {"m": ids["m"]})
        assert "row-level security" in str(teammate.value).lower()

        with pytest.raises(Exception) as denied:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE helix_app"))
                await conn.execute(text("SELECT set_config('helix.auth_email', :e, true)"), {"e": f"other-{s}@example.com"})
                await conn.execute(text(
                    "INSERT INTO users (id, email, password_hash, role) VALUES (:i, :e, 'x', 'customer')"
                ), {"i": f"rlsx_{s}", "e": f"new-{s}@example.com"})
        assert "row-level security" in str(denied.value).lower()

        async with conn.begin():
            await conn.execute(text("SET LOCAL ROLE helix_app"))
            await conn.execute(text("SELECT set_config('helix.auth_email', :e, true)"), {"e": f"new-{s}@example.com"})
            await conn.execute(text(
                "INSERT INTO users (id, email, password_hash, role) VALUES (:i, :e, 'x', 'customer')"
            ), {"i": f"rlsy_{s}", "e": f"new-{s}@example.com"})
