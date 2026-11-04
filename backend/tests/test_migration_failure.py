"""Real-PostgreSQL regression for schema/version atomicity across revisions.

Uses a uniquely named disposable database, never the configured app database.
The migration identity must be able to create databases and event triggers.
"""

from __future__ import annotations

import os
import shutil
import uuid

import pytest

from scripts import prove_prod_schema_reconcile as proof


@pytest.mark.parametrize("url", [
    "postgresql://localhost/test?host=db.example.invalid",
    "postgresql://db.example.invalid/test",
    "postgresql:///test",
])
def test_proof_refuses_non_loopback_or_implicit_database_hosts(monkeypatch, url):
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    with pytest.raises(SystemExit, match="loopback"):
        proof._admin_dsn()


def test_proof_does_not_fall_back_to_the_application_database(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/application")
    with pytest.raises(SystemExit, match="explicit loopback"):
        proof._admin_dsn()


def test_proof_refuses_an_unscoped_database_name():
    with pytest.raises(SystemExit, match="disposable"):
        proof._recreate("postgres")


def test_failure_after_tenancy_preserves_stamp_and_retry_reaches_head():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://", "postgresql+asyncpg://")):
        pytest.skip("migration failure regression requires TEST_DATABASE_URL for real PostgreSQL")
    if shutil.which("psql") is None:
        pytest.skip("migration failure regression requires the PostgreSQL psql client")

    database = f"helix_migration_fail_{uuid.uuid4().hex[:12]}"
    try:
        proof.prove_failure_after_tenancy_is_retryable(database)
    finally:
        proof._psql(
            proof._admin_dsn(),
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{database}' AND pid <> pg_backend_pid()",
        )
        proof._psql(proof._admin_dsn(), f"DROP DATABASE IF EXISTS {database}")
