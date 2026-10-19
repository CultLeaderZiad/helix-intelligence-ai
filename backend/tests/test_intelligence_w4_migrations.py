"""Migration checks against throwaway loopback PostgreSQL databases only.

Opt in with W4_POSTGRES_ADMIN_URL, a local role allowed to CREATE DATABASE.
W4_DISPOSABLE_DATABASE_URL is an equivalent explicit opt-in for CI.
Each test creates/drops its own helix_w4_test_<uuid>; DATABASE_URL is never used
as an administrative fallback. No production host or existing schema is reset.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import uuid

import asyncpg
import pytest
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
PRE_ALIGNMENT = "a1b2c3d4e5f6"
ALIGNMENT = "b1c2d3e4f5a6"
W3 = "a9d4e6f8c2b0"
W4 = "b7e4c9a1d2f0"


async def _sql_async(url: str, sql: str, *args):
    parsed = make_url(url)
    conn = await asyncpg.connect(
        host=parsed.query.get("host", parsed.host), port=parsed.port or 5432,
        user=parsed.username, password=parsed.password, database=parsed.database,
    )
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


def sql(url: str, statement: str, *args):
    return asyncio.run(_sql_async(url, statement, *args))


def migrate(url: str, target: str = "head", *, direction: str = "upgrade", ok: bool = True):
    env = {**os.environ, "DATABASE_URL": url, "TEST_DATABASE_URL": url.replace("%", "%%"),
           "SECRET_KEY": "w4-disposable-test-signing-key-not-production", "ENVIRONMENT": "test"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", direction, target], cwd=BACKEND,
        env=env, text=True, capture_output=True, timeout=90,
    )
    if ok:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, "dirty migration unexpectedly succeeded"
    return result.stdout + result.stderr


@pytest.fixture
def disposable_database():
    raw = os.environ.get("W4_POSTGRES_ADMIN_URL") or os.environ.get("W4_DISPOSABLE_DATABASE_URL")
    if not raw:
        pytest.skip("set W4_POSTGRES_ADMIN_URL or W4_DISPOSABLE_DATABASE_URL for disposable PostgreSQL checks")
    admin = make_url(raw)
    if admin.get_backend_name() != "postgresql" or admin.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("W4 tests refuse non-loopback PostgreSQL administration")
    socket_host = admin.query.get("host")
    if socket_host is not None and (not isinstance(socket_host, str) or not socket_host.startswith("/")):
        pytest.fail("W4 tests refuse a query-string host override unless it is a local Unix socket")
    name = "helix_w4_test_" + uuid.uuid4().hex
    sql(raw, f'CREATE DATABASE "{name}"')
    url = admin.set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    try:
        yield url
    finally:
        # Never kill connections or touch a database supplied by the caller.
        # Only this fixture's generated database is eligible for deletion.
        sql(raw, f'DROP DATABASE "{name}"')


def seed_owner(url: str):
    sql(url, "INSERT INTO users (id,email,password_hash) VALUES ('w4_user','w4@example.test','x')")
    sql(url, "INSERT INTO organizations (id,name,owner_id) VALUES ('w4_org','W4','w4_user')")


def test_alignment_downgrade_helpers_are_module_scoped():
    path = BACKEND / "alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py"
    spec = importlib.util.spec_from_file_location("w4_alignment", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "table_exists", None))
    assert callable(getattr(module, "column_exists", None))


def test_fresh_chain_preserves_w3_identity_and_rls(disposable_database):
    url = disposable_database
    migrate(url)
    assert sql(url, "SELECT version_num FROM alembic_version")[0][0] == W4
    indexes = {row[0] for row in sql(url, "SELECT indexname FROM pg_indexes WHERE tablename='scrape_jobs'")}
    assert "uq_scrape_jobs_active_identity" in indexes
    assert "uq_scrape_jobs_active_query" not in indexes
    protected = sql(url, "SELECT relrowsecurity FROM pg_class WHERE oid='scrape_jobs'::regclass")[0][0]
    assert protected is True
    policy = sql(url, "SELECT qual FROM pg_policies WHERE tablename='scrape_jobs'")
    assert policy and any("helix.org_ids" in row[0] for row in policy if row[0])


def test_upgrade_backfills_only_stored_job_evidence_and_roundtrips(disposable_database):
    url = disposable_database
    migrate(url, PRE_ALIGNMENT)
    seed_owner(url)
    sql(url, """INSERT INTO leadgen_jobs (id,org_id,created_at,started_at)
        VALUES ('w4_job','w4_org',NULL,'2026-01-02T03:04:05Z')""")
    sql(url, """INSERT INTO leadgen_leads (id,org_id,job_id,created_at)
        VALUES ('w4_lead','w4_org','w4_job',NULL)""")
    migrate(url, ALIGNMENT)
    rows = sql(url, "SELECT created_at FROM leadgen_leads WHERE id='w4_lead'")
    assert rows[0][0].isoformat() == "2026-01-02T03:04:05+00:00"
    migrate(url, PRE_ALIGNMENT, direction="downgrade")
    assert sql(url, "SELECT version_num FROM alembic_version")[0][0] == PRE_ALIGNMENT
    assert sql(url, "SELECT id FROM leadgen_leads")[0][0] == "w4_lead"
    migrate(url)
    assert sql(url, "SELECT created_at FROM leadgen_jobs WHERE id='w4_job'")[0][0] == rows[0][0]


def test_unknown_timestamp_aborts_without_partial_ddl_or_row_loss(disposable_database):
    url = disposable_database
    migrate(url, PRE_ALIGNMENT)
    sql(url, "INSERT INTO leadgen_worker_heartbeat (id,updated_at) VALUES ('w4_unknown',NULL)")
    output = migrate(url, ALIGNMENT, ok=False)
    assert "repair from source evidence" in output
    assert sql(url, "SELECT version_num FROM alembic_version")[0][0] == PRE_ALIGNMENT
    assert sql(url, "SELECT updated_at FROM leadgen_worker_heartbeat WHERE id='w4_unknown'")[0][0] is None
    assert not sql(url, "SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='full_name'")
    # Repair is explicit and evidence-supplied; the migration never guesses it.
    sql(url, "UPDATE leadgen_worker_heartbeat SET updated_at='2026-01-02T03:04:05Z'")
    migrate(url)


def test_duplicate_active_jobs_abort_transaction_instead_of_swallowing_ddl(disposable_database):
    url = disposable_database
    migrate(url, PRE_ALIGNMENT)
    seed_owner(url)
    sql(url, """INSERT INTO scrape_jobs (id,org_id,query,status,created_at) VALUES
        ('w4_a','w4_org','Shoes','running',now()), ('w4_b','w4_org','shoes','queued',now())""")
    output = migrate(url, ALIGNMENT, ok=False)
    assert "uq_scrape_jobs_active_query" in output
    assert sql(url, "SELECT version_num FROM alembic_version")[0][0] == PRE_ALIGNMENT
    assert len(sql(url, "SELECT id FROM scrape_jobs")) == 2
    assert not sql(url, "SELECT 1 FROM pg_tables WHERE tablename='monitors'")


def test_forward_repair_reaches_existing_w3_and_downgrade_is_non_destructive(disposable_database):
    url = disposable_database
    migrate(url, W3)
    seed_owner(url)
    sql(url, "ALTER TABLE leadgen_jobs ALTER COLUMN created_at DROP NOT NULL")
    sql(url, """INSERT INTO leadgen_jobs (id,org_id,created_at,started_at)
        VALUES ('w4_existing','w4_org',NULL,'2026-01-02T03:04:05Z')""")
    sql(url, "DROP INDEX ix_creatives_brand_name")
    migrate(url)
    assert sql(url, "SELECT created_at FROM leadgen_jobs WHERE id='w4_existing'")[0][0] is not None
    assert sql(url, "SELECT 1 FROM pg_indexes WHERE indexname='ix_creatives_brand_name'")
    migrate(url, W3, direction="downgrade")
    assert sql(url, "SELECT id FROM leadgen_jobs")[0][0] == "w4_existing"
    migrate(url)


def test_forward_dirty_abort_rolls_back_evidence_backfill_and_version(disposable_database):
    url = disposable_database
    migrate(url, W3)
    seed_owner(url)
    sql(url, "ALTER TABLE leadgen_jobs ALTER COLUMN created_at DROP NOT NULL")
    sql(url, "ALTER TABLE leadgen_worker_heartbeat ALTER COLUMN updated_at DROP NOT NULL")
    sql(url, """INSERT INTO leadgen_jobs (id,org_id,created_at,started_at)
        VALUES ('w4_recoverable','w4_org',NULL,'2026-01-02T03:04:05Z')""")
    sql(url, "INSERT INTO leadgen_worker_heartbeat (id,updated_at) VALUES ('w4_unknown',NULL)")
    assert "repair from source evidence" in migrate(url, ok=False)
    assert sql(url, "SELECT version_num FROM alembic_version")[0][0] == W3
    assert sql(url, "SELECT created_at FROM leadgen_jobs WHERE id='w4_recoverable'")[0][0] is None
