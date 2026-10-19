"""Real-PostgreSQL regression tests for deny-by-default tenant RLS."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.deps import _bind_request_tenant
from app.core.tenancy import tenant_scope
from app.db.session import worker_engine, worker_session_maker
from app.models.leadgen import LeadGenJob  # noqa: F401 - register all mapped tables
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.models.work_item import WorkItem


@pytest.mark.asyncio
async def test_rls_deny_by_default_for_restricted_roles_and_worker_claims():
    if worker_engine.dialect.name != "postgresql":
        pytest.skip("RLS regression requires a real PostgreSQL database")

    suffix = uuid.uuid4().hex[:10]
    user_a = User(
        id=f"rls_user_a_{suffix}",
        email=f"rls_a_{suffix}@example.test",
        password_hash="x",
        role="customer",
    )
    user_b = User(
        id=f"rls_user_b_{suffix}",
        email=f"rls_b_{suffix}@example.test",
        password_hash="x",
        role="customer",
    )
    org_a = Organization(
        id=f"rls_org_a_{suffix}",
        name="RLS A",
        owner_id=user_a.id,
        plan_id="plan_trial_default",
        plan="trial",
        status="active",
    )
    org_b = Organization(
        id=f"rls_org_b_{suffix}",
        name="RLS B",
        owner_id=user_b.id,
        plan_id="plan_trial_default",
        plan="trial",
        status="active",
    )
    job_a = ScrapeJob(
        id=f"rls_job_a_{suffix}", org_id=org_a.id, query="private a", status="succeeded"
    )
    job_b = ScrapeJob(
        id=f"rls_job_b_{suffix}", org_id=org_b.id, query="private b", status="succeeded"
    )
    item = WorkItem(
        id=f"rls_work_{suffix}",
        org_id=org_b.id,
        user_id=user_b.id,
        kind="discover",
        job_id=job_b.id,
        payload={},
        status="queued",
        attempt_count=0,
        max_attempts=3,
        idempotency_key=f"rls_key_{suffix}",
        available_at=datetime.now(timezone.utc),
    )

    async with worker_session_maker() as db:
        db.add_all([user_a, user_b])
        await db.flush()
        db.add_all([org_a, org_b])
        await db.flush()
        db.add_all([job_a, job_b, item])
        await db.commit()

    # This role is not an owner and receives table privileges only through
    # membership in helix_app, matching the restricted application identity.
    test_role = f"helix_rls_login_{suffix}"
    async with worker_engine.begin() as conn:
        await conn.execute(
            text(f"CREATE ROLE {test_role} NOLOGIN NOSUPERUSER NOBYPASSRLS INHERIT")
        )
        await conn.execute(text(f"GRANT helix_app TO {test_role}"))

    engine = create_async_engine(
        worker_engine.url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    try:
        async with engine.connect() as conn:
            # Policy catalog coverage and group-role defaults are part of the
            # migration contract; the role defaults are backup, not the RLS fix.
            policies = (
                await conn.execute(
                    text(
                        "SELECT policyname, qual, with_check "
                        "FROM pg_policies WHERE schemaname = 'public' "
                        "AND policyname LIKE '%_tenant_isolation' ORDER BY policyname"
                    )
                )
            ).all()
            assert len(policies) == 34
            assert all(
                "helix.enforce" not in f"{row.qual} {row.with_check}"
                for row in policies
            )
            role_defaults = (
                await conn.execute(
                    text(
                        "SELECT rolname, rolconfig FROM pg_roles "
                        "WHERE rolname IN ('helix_app', 'helix_worker')"
                    )
                )
            ).all()
            assert {row.rolname for row in role_defaults} == {"helix_app", "helix_worker"}
            assert all("helix.enforce=1" in (row.rolconfig or []) for row in role_defaults)
            await conn.commit()

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                # No org/user settings: missing enforcement context must not
                # grant access to either the organization table or tenant rows.
                assert (await conn.execute(text("SELECT count(*) FROM organizations"))).scalar_one() == 0
                assert (await conn.execute(text("SELECT count(*) FROM scrape_jobs"))).scalar_one() == 0

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
                assert (await conn.execute(text("SELECT count(*) FROM organizations"))).scalar_one() == 0
                assert (await conn.execute(text("SELECT count(*) FROM scrape_jobs"))).scalar_one() == 0

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                await conn.execute(
                    text("SELECT set_config('helix.org_ids', :org_id, true)"),
                    {"org_id": org_a.id},
                )
                orgs = (
                    await conn.execute(text("SELECT id FROM organizations ORDER BY id"))
                ).scalars().all()
                jobs = (
                    await conn.execute(text("SELECT id FROM scrape_jobs ORDER BY id"))
                ).scalars().all()
                assert orgs == [org_a.id]
                assert jobs == [job_a.id]

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                await conn.execute(
                    text("SELECT set_config('helix.org_ids', :org_id, true)"),
                    {"org_id": org_b.id},
                )
                assert (
                    await conn.execute(text("SELECT id FROM organizations"))
                ).scalars().all() == [org_b.id]
                assert (
                    await conn.execute(text("SELECT id FROM scrape_jobs"))
                ).scalars().all() == [job_b.id]

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                await conn.execute(text("SELECT set_config('helix.platform_admin', '1', true)"))
                assert (await conn.execute(text("SELECT count(*) FROM organizations"))).scalar_one() >= 2
                assert (await conn.execute(text("SELECT count(*) FROM scrape_jobs"))).scalar_one() >= 2

            async with conn.begin():
                await conn.execute(text(f"SET LOCAL ROLE {test_role}"))
                with tenant_scope([], user_a.id, platform_admin=False, enforce=True):
                    async with AsyncSession(bind=conn, expire_on_commit=False) as db:
                        await _bind_request_tenant(db, user_a)
                        visible = (
                            await db.execute(text("SELECT id FROM organizations ORDER BY id"))
                        ).scalars().all()
                        assert visible == [org_a.id]

            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE helix_worker"))
                await conn.execute(
                    text("SELECT set_config('helix.worker_claim', '1', true)")
                )
                await conn.execute(
                    text("SELECT set_config('helix.worker_id', 'rls-worker-test', true)")
                )
                claimed = (
                    await conn.execute(
                        text(
                            "SELECT id FROM work_items WHERE status = 'queued' "
                            "AND available_at <= now() AND cancel_requested IS NULL "
                            "ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED"
                        )
                    )
                ).scalar_one()
                assert claimed == item.id
                result = await conn.execute(
                    text(
                        "UPDATE work_items SET status = 'leased', "
                        "lease_owner = 'rls-worker-test', "
                        "lease_until = now() + interval '2 minutes' WHERE id = :id RETURNING id"
                    ),
                    {"id": claimed},
                )
                assert result.scalar_one() == item.id
    finally:
        await engine.dispose()
        async with worker_engine.begin() as conn:
            await conn.execute(text(f"REVOKE helix_app FROM {test_role}"))
            await conn.execute(text(f"DROP ROLE {test_role}"))
