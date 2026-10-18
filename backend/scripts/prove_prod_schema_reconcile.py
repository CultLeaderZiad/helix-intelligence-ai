"""Prove a production-shaped database can reach Alembic head.

Production was stamped at c4d92e1f7a8b while its tables were built partly
outside Alembic. This script builds that drift on a disposable database,
upgrades to head, and checks the model. It also upgrades an empty database
and checks that a forced failure inside the tenancy migration does not leave
its new tables committed.

Usage (from backend/):
    TEST_DATABASE_URL=postgresql+asyncpg://helix:helix@127.0.0.1:5432/postgres \
    python scripts/prove_prod_schema_reconcile.py
"""

from __future__ import annotations

import os
import subprocess
import sys


PROD_STAMP = "c4d92e1f7a8b"
BEFORE_TENANCY = "d5e8c0a1b2f3"
DRIFT_DB = os.environ.get("PROVE_DRIFT_DB", "helix_w2_prodlike")
EMPTY_DB = os.environ.get("PROVE_EMPTY_DB", "helix_w2_emptyproof")
FAIL_DB = os.environ.get("PROVE_FAIL_DB", "helix_w2_rolefail")


def _admin_dsn() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
    if not url:
        raise SystemExit("Set TEST_DATABASE_URL to an admin Postgres URL")
    url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    # Connect to the maintenance database when creating and dropping others.
    if "/" in url.rsplit("@", 1)[-1]:
        head, _db = url.rsplit("/", 1)
        return head + "/postgres"
    return url


def _db_dsn(name: str) -> str:
    return _admin_dsn().rsplit("/", 1)[0] + "/" + name


def _psql(dsn: str, statement: str) -> str:
    result = subprocess.run(
        ["psql", dsn, "-v", "ON_ERROR_STOP=1", "-At", "-c", statement],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"psql failed: {statement[:120]}")
    return result.stdout.strip()


def _recreate(name: str) -> None:
    admin = _admin_dsn()
    _psql(
        admin,
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
    )
    _psql(admin, f"DROP DATABASE IF EXISTS {name}")
    _psql(admin, f"CREATE DATABASE {name} OWNER helix")


def _alembic(*args: str, database: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = "postgresql+asyncpg://" + _db_dsn(database).split("://", 1)[1]
    env.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars")
    env.setdefault("CREDENTIAL_ENCRYPTION_KEY", "credential-key-not-the-secret-32b")
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("USE_MOCKS", "false")
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        text=True,
        capture_output=True,
    )


def _must(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"{label} failed with exit {result.returncode}")
    print(f"ok {label}")


def _sql(database: str, statement: str, params=None):
    del params
    text = _psql(_db_dsn(database), statement)
    if not text:
        return []
    return [tuple(line.split("|")) for line in text.splitlines()]


def _version(database: str) -> str:
    return _sql(database, "SELECT version_num FROM alembic_version")[0][0]


def _scalar(database: str, statement: str):
    rows = _sql(database, statement)
    if not rows or rows[0][0] == "":
        return None
    return rows[0][0]


def _apply_prod_drift(database: str) -> None:
    statements = [
        """
        INSERT INTO users (id, email, password_hash, role, is_suspended, has_completed_onboarding)
        VALUES ('user_prod', 'owner@example.com', 'x', 'customer', false, false)
        """,
        """
        INSERT INTO organizations (
            id, name, owner_id, plan_id, plan, credit_balance, credits_used,
            daily_credits_used_today, status
        )
        VALUES (
            'org_prod', 'Prod', 'user_prod', 'plan_trial_default', 'trial',
            25, 0, 0, 'active'
        )
        """,
        "DELETE FROM plans WHERE id = 'plan_enterprise_custom'",
        "DROP TABLE IF EXISTS saved_creatives, organization_invites, organization_members, notifications, external_api_usage CASCADE",
        "ALTER TABLE api_keys RENAME COLUMN prefix TO key_prefix",
        "ALTER TABLE api_keys ADD COLUMN scopes jsonb",
        "ALTER TABLE api_keys ADD COLUMN expires_at timestamptz",
        """
        INSERT INTO api_keys (id, org_id, user_id, name, key_hash, key_prefix, is_active, scopes)
        VALUES ('key_prod', 'org_prod', 'user_prod', 'demo', 'hash', 'hlx_live_ab', true, '["discover"]'::jsonb)
        """,
        "DROP INDEX IF EXISTS ix_usage_logs_job_id",
        "DROP INDEX IF EXISTS ix_usage_logs_provider",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS job_id",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS operation",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS units",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS cost_usd",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS credits_deducted",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS metadata_json",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS tokens_used",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS requests_used",
        "ALTER TABLE usage_logs DROP COLUMN IF EXISTS provider",
        "ALTER TABLE usage_logs ADD COLUMN feature_name text",
        "ALTER TABLE usage_logs ADD COLUMN credits_charged double precision",
        "ALTER TABLE usage_logs ADD COLUMN provider_cost_usd double precision",
        "ALTER TABLE usage_logs ADD COLUMN metadata jsonb",
        """
        INSERT INTO usage_logs (
            id, user_id, org_id, feature_name, credits_charged, provider_cost_usd, metadata
        )
        VALUES (
            'log_prod', 'user_prod', 'org_prod', 'discover_search', 2, 0.01,
            '{"idempotency_key":"k1"}'::jsonb
        )
        """,
        "ALTER TABLE creatives DROP COLUMN IF EXISTS is_estimated",
        "ALTER TABLE creatives DROP COLUMN IF EXISTS data_source",
        "ALTER TABLE plans ALTER COLUMN feature_flags TYPE jsonb USING feature_flags::jsonb",
        "ALTER TABLE organizations ALTER COLUMN custom_feature_flags TYPE jsonb USING custom_feature_flags::jsonb",
        "UPDATE users SET is_suspended = false WHERE is_suspended IS NULL",
        "UPDATE users SET has_completed_onboarding = false WHERE has_completed_onboarding IS NULL",
        "ALTER TABLE users ALTER COLUMN is_suspended SET NOT NULL",
        "ALTER TABLE users ALTER COLUMN has_completed_onboarding SET NOT NULL",
        """
        CREATE TABLE webhook_events (
            id text PRIMARY KEY,
            event_type text,
            payload jsonb,
            processed_at timestamptz,
            created_at timestamptz
        )
        """,
        """
        CREATE TABLE media_generation_jobs (
            id text PRIMARY KEY,
            status text,
            prompt text,
            created_at timestamptz
        )
        """,
        # Defaults, nullability, foreign key, and duplicate key_hash index
        # present on the unmodified production copy.
        "ALTER TABLE api_keys ALTER COLUMN id SET DEFAULT gen_random_uuid()::varchar",
        "ALTER TABLE api_keys ALTER COLUMN is_active SET DEFAULT true",
        "ALTER TABLE api_keys ADD CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash)",
        "ALTER TABLE plans ALTER COLUMN type SET DEFAULT 'trial'",
        "ALTER TABLE plans ALTER COLUMN credit_allowance SET DEFAULT 25",
        "ALTER TABLE plans ALTER COLUMN feature_flags SET DEFAULT '{}'::jsonb",
        "ALTER TABLE usage_logs ALTER COLUMN id SET DEFAULT gen_random_uuid()::varchar",
        "ALTER TABLE usage_logs ALTER COLUMN org_id SET NOT NULL",
        "ALTER TABLE usage_logs ALTER COLUMN user_id SET NOT NULL",
        """
        ALTER TABLE usage_logs
        ADD CONSTRAINT usage_logs_org_id_fkey
        FOREIGN KEY (org_id) REFERENCES organizations (id)
        """,
        "ALTER TABLE users ALTER COLUMN is_suspended SET DEFAULT false",
        "ALTER TABLE users ALTER COLUMN has_completed_onboarding SET DEFAULT false",
    ]
    for statement in statements:
        _sql(database, statement)


def _assert_preserved(database: str) -> None:
    prefix = _sql(database, "SELECT prefix FROM api_keys WHERE id = 'key_prod'")[0][0]
    if prefix != "hlx_live_ab":
        raise SystemExit(f"api key prefix was not preserved: {prefix}")
    extras = _sql(
        database,
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'api_keys' AND column_name IN ('key_prefix', 'scopes', 'expires_at')
        """,
    )
    if extras:
        raise SystemExit(f"legacy api_keys columns remain: {extras}")
    row = _sql(
        database,
        """
        SELECT operation, credits_deducted, cost_usd, provider, idempotency_key
        FROM usage_logs WHERE id = 'log_prod'
        """,
    )[0]
    if row[0] != "discover_search" or float(row[1]) != 2.0 or float(row[2]) != 0.01 or row[3] != "legacy" or row[4] != "k1":
        raise SystemExit(f"usage log was not preserved: {row}")
    if _scalar(database, "SELECT to_regclass('public.media_generation_jobs')") is not None:
        raise SystemExit("legacy media_generation_jobs was not removed")
    shape = _sql(
        database,
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'webhook_events' AND column_name = 'request_id'
        """,
    )
    if not shape:
        raise SystemExit("webhook_events is not the model shape")
    for table in (
        "external_api_usage",
        "notifications",
        "organization_invites",
        "organization_members",
        "saved_creatives",
    ):
        if _scalar(database, f"SELECT to_regclass('public.{table}')") is None:
            raise SystemExit(f"missing table {table}")
    counts = (
        int(_sql(database, "SELECT COUNT(*) FROM users")[0][0]),
        int(_sql(database, "SELECT COUNT(*) FROM organizations")[0][0]),
        int(_sql(database, "SELECT COUNT(*) FROM plans")[0][0]),
    )
    if counts != (1, 1, 2):
        raise SystemExit(f"expected 1 user, 1 org, 2 plans, found {counts}")
    print("ok preserved user, org, plans, api key, and usage log")


def _cycle(database: str, label: str) -> None:
    _must(_alembic("upgrade", "head", database=database), f"{label} upgrade head")
    _must(_alembic("check", database=database), f"{label} alembic check")
    _must(_alembic("downgrade", "-1", database=database), f"{label} downgrade -1")
    _must(_alembic("upgrade", "head", database=database), f"{label} upgrade head again")
    _must(_alembic("check", database=database), f"{label} alembic check again")


def prove_drift() -> None:
    _recreate(DRIFT_DB)
    _must(_alembic("upgrade", PROD_STAMP, database=DRIFT_DB), "drift stamp c4d92e1f7a8b")
    _apply_prod_drift(DRIFT_DB)
    if _version(DRIFT_DB) != PROD_STAMP:
        raise SystemExit(f"drift database is not stamped at {PROD_STAMP}")
    _cycle(DRIFT_DB, "drift")
    _assert_preserved(DRIFT_DB)


def prove_empty() -> None:
    _recreate(EMPTY_DB)
    _cycle(EMPTY_DB, "empty")


def prove_tenancy_failure_rolls_back() -> None:
    _recreate(FAIL_DB)
    _must(_alembic("upgrade", BEFORE_TENANCY, database=FAIL_DB), "fail-db stamp before tenancy")
    _sql(FAIL_DB, "ALTER TABLE usage_logs DROP COLUMN operation")
    _sql(FAIL_DB, "ALTER TABLE usage_logs DROP COLUMN metadata_json")
    failed = _alembic("upgrade", "head", database=FAIL_DB)
    if failed.returncode == 0:
        raise SystemExit("tenancy upgrade succeeded without operation/metadata_json")
    if _version(FAIL_DB) != BEFORE_TENANCY:
        raise SystemExit(f"failed tenancy upgrade advanced the version to {_version(FAIL_DB)}")
    if _scalar(FAIL_DB, "SELECT to_regclass('public.pattern_quarantine')") is not None:
        raise SystemExit("pattern_quarantine was committed even though the tenancy revision failed")
    print("ok tenancy failure left the previous revision and did not commit its tables")
    _sql(FAIL_DB, "ALTER TABLE usage_logs ADD COLUMN operation VARCHAR NOT NULL DEFAULT 'discover_search'")
    _sql(FAIL_DB, "ALTER TABLE usage_logs ADD COLUMN metadata_json JSON")
    _must(_alembic("upgrade", "head", database=FAIL_DB), "fail-db upgrade after repair")
    _must(_alembic("check", database=FAIL_DB), "fail-db alembic check")


def prove_nonempty_legacy_is_refused() -> None:
    name = os.environ.get("PROVE_NONEMPTY_DB", "helix_w2_nonempty")
    _recreate(name)
    _must(_alembic("upgrade", PROD_STAMP, database=name), "nonempty stamp")
    _sql(
        name,
        """
        CREATE TABLE webhook_events (
            id text PRIMARY KEY,
            event_type text,
            payload jsonb,
            processed_at timestamptz,
            created_at timestamptz
        )
        """,
    )
    _sql(name, "INSERT INTO webhook_events (id, event_type) VALUES ('evt_1', 'delivery')")
    failed = _alembic("upgrade", "head", database=name)
    if failed.returncode == 0:
        raise SystemExit("non-empty legacy webhook_events was replaced")
    combined = failed.stdout + failed.stderr
    if "Refusing to replace public.webhook_events" not in combined:
        sys.stderr.write(combined)
        raise SystemExit("refusal did not name webhook_events")
    if _version(name) != PROD_STAMP:
        # 3c8be5787f7a may have committed before 51fc refused.
        if _version(name) not in {PROD_STAMP, "3c8be5787f7a"}:
            raise SystemExit(f"unexpected version after refusal: {_version(name)}")
    remaining = _sql(name, "SELECT event_type FROM webhook_events WHERE id = 'evt_1'")
    if not remaining or remaining[0][0] != "delivery":
        raise SystemExit("legacy webhook row was destroyed")
    print("ok non-empty legacy webhook_events was left in place")


def main() -> None:
    prove_empty()
    prove_drift()
    prove_tenancy_failure_rolls_back()
    prove_nonempty_legacy_is_refused()
    print("prod schema reconcile proof passed")


if __name__ == "__main__":
    main()
