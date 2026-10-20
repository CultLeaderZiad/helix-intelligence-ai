"""Real W4 transactions and concurrent tenant-scoped calls, never vendor IO."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
import time

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import test_intelligence_w4_migrations as migration_checks
from app.core.tenancy import bind_tenant, reset_tenant
from app.models.organization import Organization
from app.models.user import User
from app.services.billing_service import release_reservation, reserve_credits

# Reuse the guarded per-test generated database, not the process DATABASE_URL.
disposable_database = migration_checks.disposable_database


def test_actual_hmac_and_media_capability_signatures_reject_tampering(monkeypatch):
    from app.core.config import settings
    from app.core.security import verify_hmac_signature
    from app.services.storage_service import sign_capability, verify_capability

    key = "w4-synthetic-signature-key-not-a-real-credential"
    monkeypatch.setattr(settings, "SECRET_KEY", key)
    body = b'{"event_id":"w4-synthetic","status":"completed"}'
    signature = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    assert verify_hmac_signature(body, signature, key)
    assert verify_hmac_signature(body, f"sha256={signature}", key)
    assert not verify_hmac_signature(body + b" ", signature, key)
    assert not verify_hmac_signature(body, signature, key + "wrong")
    assert not verify_hmac_signature(body, "not-a-signature", key)

    expiry = int(time.time()) + 60
    signed = sign_capability("w4.png", expiry, "org_a", "user_a", "3")
    assert verify_capability("w4.png", signed, str(expiry), "org_a", "user_a", "3")
    assert not verify_capability("other.png", signed, str(expiry), "org_a", "user_a", "3")
    assert not verify_capability("w4.png", signed, str(expiry), "org_b", "user_a", "3")
    assert not verify_capability("w4.png", signed, str(expiry), "org_a", "user_b", "3")
    assert not verify_capability("w4.png", signed, str(expiry), "org_a", "user_a", "4")
    expired = int(time.time()) - 60
    assert not verify_capability("w4.png", sign_capability("w4.png", expired), str(expired))


@pytest.fixture
def migrated_database(disposable_database):
    migration_checks.migrate(disposable_database)
    return disposable_database


@asynccontextmanager
async def sessions(url, *, restricted=False, pooled=False):
    options = {"pool_size": 1, "max_overflow": 0} if pooled else {"poolclass": NullPool}
    engine = create_async_engine(url, **options)
    if restricted:
        @event.listens_for(engine.sync_engine, "connect")
        def _restricted_role(connection, record):
            cursor = connection.cursor()
            cursor.execute("SET ROLE helix_app")
            cursor.close()
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def seed_two_tenants(factory):
    async with factory() as db:
        for suffix in ("a", "b"):
            db.add(User(id=f"w4_user_{suffix}", email=f"w4_{suffix}@example.test", password_hash="x", role="customer"))
        await db.flush()
        for suffix in ("a", "b"):
            db.add(Organization(id=f"w4_org_{suffix}", owner_id=f"w4_user_{suffix}", name=suffix,
                                plan="pro", credit_balance=5.0, status="active"))
        await db.commit()


@pytest.mark.asyncio
async def test_two_tenant_concurrent_retries_debit_and_compensate_once(migrated_database):
    async with sessions(migrated_database) as owner:
        await seed_two_tenants(owner)
    async with sessions(migrated_database, restricted=True) as factory:
        barrier = asyncio.Barrier(4)

        async def reserve(suffix):
            token = bind_tenant(user_id=f"w4_user_{suffix}", org_ids=[f"w4_org_{suffix}"])
            try:
                async with factory() as db:
                    assert await db.scalar(text("SELECT current_user")) == "helix_app"
                    org = await db.get(Organization, f"w4_org_{suffix}")
                    await barrier.wait()
                    result = await reserve_credits(db, org, f"w4_user_{suffix}", 2.0, "w4_hold",
                                                   idempotency_key="same-key-across-tenants")
                    return suffix, result.id
            finally:
                reset_tenant(token)

        outcomes = await asyncio.wait_for(asyncio.gather(*(reserve(s) for s in ("a", "a", "b", "b"))), 20)
        ids = {suffix: {rid for tenant, rid in outcomes if tenant == suffix} for suffix in ("a", "b")}
        assert all(len(value) == 1 for value in ids.values())
        assert ids["a"] != ids["b"]
        async with sessions(migrated_database) as owner:
            async with owner() as db:
                assert list((await db.execute(text("SELECT credit_balance FROM organizations ORDER BY id"))).scalars()) == [3.0, 3.0]
                assert await db.scalar(text("SELECT count(*) FROM credit_ledger")) == 2
                assert await db.scalar(text("SELECT count(*) FROM credit_reservations")) == 2
                assert await db.scalar(text("SELECT count(*) FROM operation_idempotency")) == 2

        async def release(suffix):
            token = bind_tenant(user_id=f"w4_user_{suffix}", org_ids=[f"w4_org_{suffix}"])
            try:
                async with factory() as db:
                    return suffix, await release_reservation(db, next(iter(ids[suffix])), "w4_compensation")
            finally:
                reset_tenant(token)

        released = await asyncio.wait_for(asyncio.gather(*(release(s) for s in ("a", "a", "b", "b"))), 20)
        assert sum(result for _, result in released) == 2
    async with sessions(migrated_database) as owner:
        async with owner() as db:
            assert list((await db.execute(text("SELECT credit_balance FROM organizations ORDER BY id"))).scalars()) == [5.0, 5.0]
            assert await db.scalar(text("SELECT count(*) FROM credit_ledger WHERE entry_kind='refund'")) == 2
            assert await db.scalar(text("SELECT count(*) FROM usage_logs WHERE operation='refund_w4_compensation'")) == 2


@pytest.mark.asyncio
async def test_real_flushed_hold_rolls_back_on_precommit_failure(migrated_database):
    async with sessions(migrated_database) as factory:
        await seed_two_tenants(factory)
        with pytest.raises(RuntimeError, match="synthetic precommit crash"):
            async with factory() as db:
                org = await db.get(Organization, "w4_org_a")

                @event.listens_for(db.sync_session, "before_commit", once=True)
                def _crash(session):
                    # reserve_credits already flushed the balance and hold to
                    # PostgreSQL. A failing commit must roll the entire hold back.
                    raise RuntimeError("synthetic precommit crash")

                await reserve_credits(db, org, "w4_user_a", 2.0, "w4_crash", idempotency_key="crash")
        async with factory() as db:
            assert await db.scalar(select(Organization.credit_balance).where(Organization.id == "w4_org_a")) == 5.0
            for table in ("credit_reservations", "credit_ledger", "operation_idempotency", "usage_logs"):
                assert await db.scalar(text(f"SELECT count(*) FROM {table}")) == 0


@pytest.mark.asyncio
async def test_reused_restricted_connection_clears_tenant_context_after_commit_and_rollback(migrated_database):
    async with sessions(migrated_database) as owner:
        await seed_two_tenants(owner)
    async with sessions(migrated_database, restricted=True, pooled=True) as factory:
        for suffix in ("a", "b"):
            token = bind_tenant(user_id=f"w4_user_{suffix}", org_ids=[f"w4_org_{suffix}"])
            try:
                async with factory() as db:
                    assert await db.scalar(text("SELECT current_user")) == "helix_app"
                    assert list((await db.execute(select(Organization.id))).scalars()) == [f"w4_org_{suffix}"]
                    await db.commit()
                    assert list((await db.execute(select(Organization.id))).scalars()) == [f"w4_org_{suffix}"]
                    await db.rollback()
            finally:
                reset_tenant(token)
            async with factory() as db:
                assert list((await db.execute(select(Organization.id))).scalars()) == []
                assert await db.scalar(text("SELECT coalesce(current_setting('helix.org_ids', true), '')")) == ""
