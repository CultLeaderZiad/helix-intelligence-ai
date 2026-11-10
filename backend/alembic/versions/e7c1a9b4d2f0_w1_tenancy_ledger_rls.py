"""W1 tenancy ownership, decimal ledger, and row-level security.

Revision ID: e7c1a9b4d2f0
Revises: d5e8c0a1b2f3
Create Date: 2026-10-18 20:10:00.000000

Forward-only repair. Does not rewrite an already-deployed revision.
Downgrade restores quarantined patterns and drops the new objects.
"""

from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


revision: str = "e7c1a9b4d2f0"
down_revision: Union[str, Sequence[str], None] = "d5e8c0a1b2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SECRET_KEYS = {
    "custom_api_key",
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "authorization",
    "cookie",
    "hunter_api_key",
    "linkedin_cookie",
    "linkedin_byok_cookie",
    "private_key",
    "client_secret",
}

# Direct tenant tables: a row is visible when its org_id is in the
# transaction-local helix.org_ids list.
_DIRECT_ORG_TABLES = (
    "scrape_jobs",
    "external_api_usage",
    "leadgen_jobs",
    "leadgen_leads",
    "media_jobs",
    "monitors",
    "notifications",
    "organization_invites",
    "playbooks",
    "saved_creatives",
    "scout_jobs",
    "scout_leads",
    "scout_maps_jobs",
    "scout_maps_leads",
    "simulation_reports",
    "support_tickets",
    "usage_logs",
    "workspace_provider_credentials",
    "patterns",
    "operation_idempotency",
    "credit_reservations",
    "credit_ledger",
)

_INDIRECT_PREDICATES = {
    "creatives": """EXISTS (
        SELECT 1 FROM scrape_jobs j
        WHERE j.id = creatives.job_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "ai_insights": """EXISTS (
        SELECT 1 FROM creatives c
        JOIN scrape_jobs j ON j.id = c.job_id
        WHERE c.id = ai_insights.creative_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "creative_scores": """EXISTS (
        SELECT 1 FROM creatives c
        JOIN scrape_jobs j ON j.id = c.job_id
        WHERE c.id = creative_scores.creative_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_runs": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_runs.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_creatives": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_creatives.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_events": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_events.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "support_ticket_replies": """EXISTS (
        SELECT 1 FROM support_tickets t
        WHERE t.id = support_ticket_replies.ticket_id
          AND t.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
}


def _is_secret(name: str) -> bool:
    lowered = str(name or "").lower().replace("-", "_")
    if lowered in _SECRET_KEYS:
        return True
    return (
        lowered.endswith("_api_key")
        or lowered.endswith("_secret")
        or lowered.endswith("_token")
        or lowered.endswith("_password")
        or "api_key" in lowered
    )


def _scrub(value):
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items() if not _is_secret(key)}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def _policy_sql(predicate: str) -> str:
    return f"""(
        current_setting('helix.enforce', true) IS DISTINCT FROM '1'
        OR current_setting('helix.platform_admin', true) = '1'
        OR {predicate}
    )"""


def _enable_policy(table: str, predicate: str) -> None:
    expression = _policy_sql(predicate)
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_tenant_isolation ON {table} "
        f"FOR ALL USING {expression} WITH CHECK {expression}"
    )


def _disable_policy(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def _create_roles() -> None:
    # Bootstrap cluster-wide identities before any revision-local schema work.
    # Entering autocommit commits an open transaction, so this must remain the
    # first upgrade step. Per-revision transactions keep earlier stamps durable;
    # everything after this block commits atomically with this revision's stamp.
    # Roles may survive a failed upgrade, which is safe because this is idempotent.
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN
                    CREATE ROLE helix_app NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN
                    CREATE ROLE helix_worker NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
                END IF;
            END
            $$;
            """
        )
        op.execute("GRANT helix_app TO CURRENT_USER")
        op.execute("GRANT helix_worker TO CURRENT_USER")


def _drop_roles() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM helix_app, helix_worker")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM helix_app, helix_worker")
    op.execute("REVOKE USAGE ON SCHEMA public FROM helix_app, helix_worker")
    # Role DDL is transactional in PostgreSQL. Keep it in the same transaction
    # as the schema downgrade and version stamp. Cluster-wide dependencies in
    # other databases may prevent deletion; leave those shared roles in place.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN
                BEGIN
                    EXECUTE 'REVOKE helix_worker FROM CURRENT_USER';
                    DROP ROLE helix_worker;
                EXCEPTION
                    WHEN undefined_object THEN NULL;
                    WHEN dependent_objects_still_exist THEN NULL;
                END;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN
                BEGIN
                    EXECUTE 'REVOKE helix_app FROM CURRENT_USER';
                    DROP ROLE helix_app;
                EXCEPTION
                    WHEN undefined_object THEN NULL;
                    WHEN dependent_objects_still_exist THEN NULL;
                END;
            END IF;
        END
        $$;
        """
    )


def _usage_log_columns() -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("usage_logs"):
        return set()
    return {col["name"] for col in insp.get_columns("usage_logs")}


def upgrade() -> None:
    _create_roles()
    op.create_table(
        "pattern_quarantine",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("family", sa.String(), nullable=False),
        sa.Column("prevalence", sa.Float(), nullable=False),
        sa.Column("lift_index", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("patterns", sa.Column("org_id", sa.String(), nullable=True))
    op.create_index("ix_patterns_org_id", "patterns", ["org_id"])
    op.create_foreign_key("fk_patterns_org_id", "patterns", "organizations", ["org_id"], ["id"])
    op.execute(
        """
        UPDATE patterns AS p
        SET org_id = j.org_id
        FROM scrape_jobs AS j
        WHERE p.job_id = j.id
          AND p.org_id IS NULL
          AND j.org_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO pattern_quarantine (id, job_id, label, family, prevalence, lift_index, reason)
        SELECT p.id, p.job_id, p.label, p.family, p.prevalence, p.lift_index,
               CASE WHEN p.job_id IS NULL THEN 'null_job' ELSE 'unassignable_org' END
        FROM patterns AS p
        WHERE p.org_id IS NULL
        """
    )
    op.execute("DELETE FROM patterns WHERE org_id IS NULL")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION helix_patterns_assign_org()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.org_id IS NULL AND NEW.job_id IS NOT NULL THEN
                SELECT org_id INTO NEW.org_id FROM scrape_jobs WHERE id = NEW.job_id;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER patterns_assign_org
        BEFORE INSERT OR UPDATE ON patterns
        FOR EACH ROW
        EXECUTE FUNCTION helix_patterns_assign_org()
        """
    )

    usage_cols = _usage_log_columns()
    for name in ("idempotency_key", "payload_hash", "reservation_id", "ledger_id"):
        if name not in usage_cols:
            op.add_column("usage_logs", sa.Column(name, sa.String(), nullable=True))
    usage_cols = _usage_log_columns()
    # Older production rows stored the key inside metadata, not metadata_json.
    # Skip the copy when that column was never created.
    if {"metadata_json", "operation", "id"} <= usage_cols:
        op.execute(
            """
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY org_id, operation, (metadata_json::jsonb ->> 'idempotency_key')
                           ORDER BY created_at ASC NULLS LAST, id ASC
                       ) AS n,
                       metadata_json::jsonb ->> 'idempotency_key' AS idem_key
                FROM usage_logs
                WHERE metadata_json IS NOT NULL
                  AND (metadata_json::jsonb ->> 'idempotency_key') IS NOT NULL
            )
            UPDATE usage_logs AS u
            SET idempotency_key = CASE WHEN ranked.n = 1 THEN ranked.idem_key ELSE NULL END
            FROM ranked
            WHERE u.id = ranked.id
            """
        )
    bind = op.get_bind()
    existing_uniques = {item["name"] for item in sa.inspect(bind).get_unique_constraints("usage_logs")}
    if "uq_usage_logs_org_operation_idempotency_key" not in existing_uniques:
        op.create_unique_constraint(
            "uq_usage_logs_org_operation_idempotency_key",
            "usage_logs",
            ["org_id", "operation", "idempotency_key"],
        )

    op.create_table(
        "operation_idempotency",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("usage_log_id", sa.String(), nullable=True),
        sa.Column("reservation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "operation", "idempotency_key", name="uq_operation_idempotency_org_op_key"),
    )
    op.create_index("ix_operation_idempotency_org_id", "operation_idempotency", ["org_id"])

    op.create_table(
        "credit_reservations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 6), nullable=False),
        sa.Column("media_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("payload_hash", sa.String(), nullable=True),
        sa.Column("usage_log_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_reservations_org_id", "credit_reservations", ["org_id"])
    op.create_index("ix_credit_reservations_job_id", "credit_reservations", ["job_id"])

    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("usage_log_id", sa.String(), nullable=True),
        sa.Column("reservation_id", sa.String(), nullable=True),
        sa.Column("entry_kind", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 6), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["usage_log_id"], ["usage_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_ledger_org_id", "credit_ledger", ["org_id"])
    op.create_index("ix_credit_ledger_usage_log_id", "credit_ledger", ["usage_log_id"])
    op.create_index("ix_credit_ledger_reservation_id", "credit_ledger", ["reservation_id"])

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, parameters FROM media_jobs WHERE parameters IS NOT NULL")).fetchall()
    for row in rows:
        raw = row.parameters
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                continue
        cleaned = _scrub(raw)
        if cleaned != raw:
            bind.execute(
                sa.text("UPDATE media_jobs SET parameters = CAST(:params AS json) WHERE id = :id"),
                {"params": json.dumps(cleaned), "id": row.id},
            )

    org_predicate = (
        "org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))"
    )
    for table in _DIRECT_ORG_TABLES:
        _enable_policy(table, org_predicate)
    _enable_policy(
        "organizations",
        """id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
           OR owner_id = current_setting('helix.user_id', true)""",
    )
    _enable_policy(
        "organization_members",
        """org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
           OR user_id = current_setting('helix.user_id', true)""",
    )
    for table, predicate in _INDIRECT_PREDICATES.items():
        _enable_policy(table, predicate)

    op.execute("GRANT USAGE ON SCHEMA public TO helix_app, helix_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO helix_app, helix_worker"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO helix_app, helix_worker")


def downgrade() -> None:
    for table in list(_INDIRECT_PREDICATES) + ["organizations", "organization_members", *_DIRECT_ORG_TABLES]:
        _disable_policy(table)

    op.execute("DROP TRIGGER IF EXISTS patterns_assign_org ON patterns")
    op.execute("DROP FUNCTION IF EXISTS helix_patterns_assign_org()")

    op.execute(
        """
        INSERT INTO patterns (id, job_id, label, family, prevalence, lift_index)
        SELECT id, job_id, label, family, prevalence, lift_index
        FROM pattern_quarantine
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.drop_index("ix_credit_ledger_reservation_id", table_name="credit_ledger")
    op.drop_index("ix_credit_ledger_usage_log_id", table_name="credit_ledger")
    op.drop_index("ix_credit_ledger_org_id", table_name="credit_ledger")
    op.drop_table("credit_ledger")
    op.drop_index("ix_credit_reservations_job_id", table_name="credit_reservations")
    op.drop_index("ix_credit_reservations_org_id", table_name="credit_reservations")
    op.drop_table("credit_reservations")
    op.drop_index("ix_operation_idempotency_org_id", table_name="operation_idempotency")
    op.drop_table("operation_idempotency")

    op.drop_constraint("uq_usage_logs_org_operation_idempotency_key", "usage_logs", type_="unique")
    op.drop_column("usage_logs", "ledger_id")
    op.drop_column("usage_logs", "reservation_id")
    op.drop_column("usage_logs", "payload_hash")
    op.drop_column("usage_logs", "idempotency_key")

    op.drop_constraint("fk_patterns_org_id", "patterns", type_="foreignkey")
    op.drop_index("ix_patterns_org_id", table_name="patterns")
    op.drop_column("patterns", "org_id")
    op.drop_table("pattern_quarantine")
    _drop_roles()
