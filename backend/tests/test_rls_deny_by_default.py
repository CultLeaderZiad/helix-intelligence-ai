"""Real-PostgreSQL regression tests for deny-by-default tenant RLS."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.deps import _bind_request_tenant
from app.core.tenancy import tenant_scope
from app.db.session import worker_engine, worker_session_maker
from app.models.leadgen import LeadGenJob  # noqa: F401 - register all mapped tables
from app.models.organization import Organization
from app.models.monitor import Monitor, MonitorRun
from app.models.usage_log import UsageLog
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

    now = datetime.now(timezone.utc)
    recent_failed = ScrapeJob(
        id=f"rls_recent_{suffix}", org_id=org_b.id, query="recent failure",
        status="failed", created_at=now - timedelta(days=3),
        completed_at=now - timedelta(hours=1),
    )
    old_failed = ScrapeJob(
        id=f"rls_old_{suffix}", org_id=org_b.id, query="old failure",
        status="failed", created_at=now - timedelta(days=3),
        completed_at=now - timedelta(hours=25),
    )
    monitors = [Monitor(
        id=f"rls_monitor_{kind}_{suffix}", org_id=org_b.id, user_id=user_b.id,
        name=kind, query=kind, status="paused",
    ) for kind in ("stale", "fresh", "done", "empty")]
    runs = [MonitorRun(
        id=f"rls_run_{kind}_{suffix}", monitor_id=monitor.id,
        status="succeeded" if kind == "done" else "running",
        started_at=now - timedelta(seconds=30 if kind == "fresh" else 300),
    ) for kind, monitor in zip(("stale", "fresh", "done"), monitors)]
    logs = [UsageLog(
        id=f"rls_log_{kind}_{suffix}", org_id=org_b.id, user_id=user_b.id,
        job_id=job.id, provider="test", operation="discover_search", credits_deducted=1,
    ) for kind, job in (("recent", recent_failed), ("old", old_failed))]

    async with worker_session_maker() as db:
        db.add_all([user_a, user_b])
        await db.flush()
        db.add_all([org_a, org_b])
        await db.flush()
        db.add_all([job_a, job_b, recent_failed, old_failed, item, *monitors])
        await db.flush()
        db.add_all([*runs, *logs])
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
            # Fail-closed policies must not depend on role-level GUC defaults.
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
            maintenance_policies = (await conn.execute(text(
                "SELECT qual, with_check FROM pg_policies "
                "WHERE schemaname = 'public' AND policyname LIKE '%_maintenance_%'"
            ))).all()
            assert maintenance_policies
            assert all("helix_worker" in row.qual and "helix_app" not in row.qual for row in maintenance_policies)
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

            # API identities cannot turn maintenance into a cross-tenant bypass.
            for app_role in (test_role, "helix_app"):
                async with conn.begin():
                    await conn.execute(text(f"SET LOCAL ROLE {app_role}"))
                    await conn.execute(text("SELECT set_config('helix.maintenance', '1', true)"))
                    await conn.execute(text("SELECT set_config('helix.maintenance_monitor_id', :id, true)"), {"id": monitors[0].id})
                    for table in ("scrape_jobs", "usage_logs", "monitors", "monitor_runs", "work_items", "media_jobs", "leadgen_jobs", "scout_jobs", "scout_maps_jobs"):
                        assert (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0
                    assert (await conn.execute(text("SELECT public.helix_monitor_has_stale_run(:id)"), {"id": monitors[0].id})).scalar_one() is False

            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE helix_worker"))
                await conn.execute(text("SELECT set_config('helix.maintenance', '1', true)"))
                assert (await conn.execute(text("SELECT id FROM scrape_jobs WHERE id LIKE :pattern"), {"pattern": f"rls_%_{suffix}"})).scalars().all() == [recent_failed.id]
                assert (await conn.execute(text("SELECT id FROM usage_logs WHERE id LIKE :pattern"), {"pattern": f"rls_log_%_{suffix}"})).scalars().all() == [logs[0].id]
                for monitor in monitors:
                    await conn.execute(text("SELECT set_config('helix.maintenance_monitor_id', :id, true)"), {"id": monitor.id})
                    ids = (await conn.execute(text("SELECT id FROM monitors WHERE id = :id"), {"id": monitor.id})).scalars().all()
                    assert ids == ([monitor.id] if monitor == monitors[0] else [])
                # Once the run is closed, even a remembered parent id is denied.
                await conn.execute(text("SELECT set_config('helix.org_ids', :id, true)"), {"id": org_b.id})
                await conn.execute(text("UPDATE monitor_runs SET status = 'failed' WHERE id = :id"), {"id": runs[0].id})
                await conn.execute(text("SELECT set_config('helix.org_ids', '', true)"))
                await conn.execute(text("SELECT set_config('helix.maintenance_monitor_id', :id, true)"), {"id": monitors[0].id})
                assert (await conn.execute(text("SELECT id FROM monitors WHERE id = :id"), {"id": monitors[0].id})).scalars().all() == []

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
                    await conn.execute(text("SELECT id FROM scrape_jobs ORDER BY id"))
                ).scalars().all() == sorted([job_b.id, recent_failed.id, old_failed.id])

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
                            "SELECT id FROM work_items WHERE id = :item_id AND status = 'queued' "
                            "AND available_at <= now() AND cancel_requested IS NULL "
                            "ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED"
                        ),
                        {"item_id": item.id},
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


@pytest.mark.asyncio
async def test_reconciliation_runs_with_restricted_worker_role(monkeypatch):
    """Exercise real worker maintenance reads and tenant-bound terminal writes."""
    if worker_engine.dialect.name != "postgresql":
        pytest.skip("RLS regression requires a real PostgreSQL database")
    from unittest.mock import AsyncMock
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.media_job import MediaGenerationJob
    from app.services import job_reconciliation as reconciliation
    from app.services import monitor_service

    suffix = uuid.uuid4().hex[:10]
    stale = datetime.now(timezone.utc) - timedelta(minutes=30)
    user = User(id=f"reconcile_user_{suffix}", email=f"reconcile_{suffix}@example.test", password_hash="x", role="customer")
    org = Organization(id=f"reconcile_org_{suffix}", name="Reconcile", owner_id=user.id, plan_id="plan_trial_default", plan="trial", status="active")
    job = MediaGenerationJob(id=f"reconcile_media_{suffix}", org_id=org.id, user_id=user.id, prompt="test", provider="test", status="running", created_at=stale, heartbeat_at=stale, owner_boot_id="dead-boot")
    monitor = Monitor(id=f"reconcile_monitor_{suffix}", org_id=org.id, user_id=user.id, name="test", query="test", status="paused")
    run = MonitorRun(id=f"reconcile_run_{suffix}", monitor_id=monitor.id, status="running", started_at=stale)
    async with worker_session_maker() as db:
        db.add(user)
        await db.flush()
        db.add(org)
        await db.flush()
        db.add_all([job, monitor])
        await db.flush()
        db.add(run)
        await db.commit()

    restricted = create_async_engine(
        worker_engine.url, poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "server_settings": {"role": "helix_worker"}},
    )
    notify = AsyncMock()
    monkeypatch.setattr(reconciliation, "worker_session_maker", async_sessionmaker(restricted, expire_on_commit=False))
    monkeypatch.setattr(monitor_service, "notify_run_interrupted", notify)
    try:
        rows = await reconciliation._sweep_table("media_jobs", reconciliation.MEDIA_ACTIVE, "error_message", reconciliation.MEDIA_MESSAGE)
        assert job.id in {row["id"] for row in rows}
        assert await reconciliation._sweep_monitor_runs() >= 1
        notify.assert_any_await(monitor.id)
        async with worker_session_maker() as db:
            assert (await db.execute(text("SELECT status FROM media_jobs WHERE id = :id"), {"id": job.id})).scalar_one() == "failed"
            assert (await db.execute(text("SELECT status FROM monitor_runs WHERE id = :id"), {"id": run.id})).scalar_one() == "failed"
    finally:
        await restricted.dispose()
