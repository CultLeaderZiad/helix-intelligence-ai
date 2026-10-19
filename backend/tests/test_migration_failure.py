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
