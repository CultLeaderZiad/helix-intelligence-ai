"""Reconcile databases whose schema drifted from the migration history.

The live database was built partly outside Alembic, so after upgrading it
still differs from the models: missing server defaults, four timestamp
columns without a time zone, a numeric column stored as text, a JSONB column
the models declare as JSON, nullable columns the models require, and two
foreign keys without ON DELETE CASCADE. Render's pre-deploy runs
``alembic check``, which fails on that drift.

Every step inspects the catalog and changes only what differs, so this is a
no-op on a database that already matches (e.g. a fresh install). No row is
deleted. The single data change is filling NULLs with the column's own
default before a NOT NULL is added (one row on the rehearsed copy).

Downgrade is a no-op: reverting would only reintroduce drift.

Revision ID: c9e1f3a5b7d0
Revises: b8d0f2a4c6e9
"""

from alembic import op
from sqlalchemy import text

revision = "c9e1f3a5b7d0"
down_revision = "b8d0f2a4c6e9"
branch_labels = None
depends_on = None

_MISSING_DEFAULTS = (
    ('app_updates', 'level', "'info'"),
    ('app_updates', 'is_published', 'false'),
    ('app_updates', 'show_as_banner', 'false'),
    ('app_updates', 'banner_dismissible', 'true'),
    ('app_updates', 'show_on_public', 'true'),
    ('app_updates', 'created_at', 'now()'),
    ('app_updates', 'updated_at', 'now()'),
    ('leadgen_jobs', 'status', "'queued'"),
    ('leadgen_jobs', 'stage', "'brief'"),
    ('leadgen_jobs', 'stage_index', "'0'"),
    ('leadgen_jobs', 'stages_total', "'9'"),
    ('leadgen_jobs', 'engine_default', "'stealth'"),
    ('leadgen_jobs', 'mode', "'crawl'"),
    ('leadgen_jobs', 'robots_obey', 'true'),
    ('leadgen_jobs', 'adaptive', 'true'),
    ('leadgen_jobs', 'enrich_emails', 'true'),
    ('leadgen_jobs', 'generate_outreach', 'true'),
    ('leadgen_jobs', 'proxy_mode', "'off'"),
    ('leadgen_jobs', 'leads_count', "'0'"),
    ('leadgen_jobs', 'pages_fetched', "'0'"),
    ('leadgen_jobs', 'pages_blocked', "'0'"),
    ('leadgen_jobs', 'elapsed_ms', "'0'"),
    ('leadgen_jobs', 'credits_used', "'0'"),
    ('leadgen_jobs', 'credit_budget', "'0'"),
    ('leadgen_jobs', 'created_at', 'now()'),
    ('leadgen_leads', 'extract_status', "'empty'"),
    ('leadgen_leads', 'fetch_status', "'ok'"),
    ('leadgen_leads', 'engine_used', "'stealth'"),
    ('leadgen_leads', 'email_source', "'none'"),
    ('leadgen_leads', 'phone_source', "'none'"),
    ('leadgen_leads', 'lead_score', "'0'"),
    ('leadgen_leads', 'created_at', 'now()'),
    ('leadgen_worker_heartbeat', 'browsers_ready', 'false'),
    ('leadgen_worker_heartbeat', 'proxy_mode', "'off'"),
    ('leadgen_worker_heartbeat', 'updated_at', 'now()'),
    ('monitor_creatives', 'status', "'active'"),
    ('monitor_creatives', 'missed_runs', "'0'"),
    ('monitor_creatives', 'first_seen_at', 'now()'),
    ('monitor_creatives', 'last_seen_at', 'now()'),
    ('monitor_events', 'created_at', 'now()'),
    ('monitor_runs', 'status', "'running'"),
    ('monitor_runs', 'started_at', 'now()'),
    ('monitor_runs', 'creatives_seen', "'0'"),
    ('monitor_runs', 'new_count', "'0'"),
    ('monitor_runs', 'killed_count', "'0'"),
    ('monitor_runs', 'changed_count', "'0'"),
    ('monitor_runs', 'is_baseline', 'false'),
    ('monitor_runs', 'credits_charged', "'0.0'"),
    ('monitors', 'filters', "'{}'"),
    ('monitors', 'cadence', "'daily'"),
    ('monitors', 'status', "'active'"),
    ('monitors', 'notify_in_app', 'true'),
    ('monitors', 'notify_email', 'false'),
    ('monitors', 'consecutive_failures', "'0'"),
    ('monitors', 'created_at', 'now()'),
    ('monitors', 'updated_at', 'now()'),
    ('playbooks', 'patterns', "'[]'"),
    ('playbooks', 'creatives', "'[]'"),
    ('playbooks', 'insights', "'[]'"),
    ('scout_jobs', 'status', "'queued'"),
    ('scout_jobs', 'platforms', "'[]'"),
    ('scout_jobs', 'handles', "'[]'"),
    ('scout_jobs', 'enrich_emails', 'true'),
    ('scout_jobs', 'stage', "'queued'"),
    ('scout_jobs', 'stage_label', "'Job queued'"),
    ('scout_jobs', 'stage_index', "'0'"),
    ('scout_jobs', 'stages_total', "'4'"),
    ('scout_jobs', 'logs', "'[]'"),
    ('scout_jobs', 'leads_count', "'0'"),
    ('scout_jobs', 'elapsed_ms', "'0'"),
    ('scout_jobs', 'credits_used', "'0'"),
    ('scout_jobs', 'created_at', 'now()'),
    ('scout_leads', 'followers', "'0'"),
    ('scout_leads', 'lead_score', "'0'"),
    ('scout_leads', 'sources', "'{}'"),
    ('scout_leads', 'created_at', 'now()'),
    ('scout_maps_jobs', 'status', "'queued'"),
    ('scout_maps_jobs', 'depth', "'5'"),
    ('scout_maps_jobs', 'extract_emails', 'true'),
    ('scout_maps_jobs', 'pull_socials', 'false'),
    ('scout_maps_jobs', 'stage', "'queued'"),
    ('scout_maps_jobs', 'stage_label', "'Job queued'"),
    ('scout_maps_jobs', 'stage_index', "'0'"),
    ('scout_maps_jobs', 'stages_total', "'4'"),
    ('scout_maps_jobs', 'logs', "'[]'"),
    ('scout_maps_jobs', 'results_count', "'0'"),
    ('scout_maps_jobs', 'elapsed_ms', "'0'"),
    ('scout_maps_jobs', 'credits_used', "'0'"),
    ('scout_maps_jobs', 'created_at', 'now()'),
    ('scout_maps_leads', 'emails_found', "'[]'"),
    ('scout_maps_leads', 'socials', "'{}'"),
    ('scout_maps_leads', 'metadata_raw', "'{}'"),
    ('scout_maps_leads', 'created_at', 'now()'),
    ('simulation_reports', 'data_source', "'simulated'"),
    ('simulation_reports', 'is_estimated', 'true'),
    ('support_ticket_replies', 'is_admin', 'false'),
    ('support_tickets', 'type', "'feedback'"),
    ('support_tickets', 'status', "'open'"),
    ('support_tickets', 'context_data', "'{}'"),
    ('workspace_provider_credentials', 'status', "'connected'"),
    ('workspace_provider_credentials', 'credential_mode', "'managed'"),
    ('workspace_provider_credentials', 'created_at', 'now()'),
    ('workspace_provider_credentials', 'updated_at', 'now()'),
)

_TIMESTAMPTZ = (
    ("app_updates", "starts_at"),
    ("app_updates", "ends_at"),
    ("app_updates", "created_at"),
    ("app_updates", "updated_at"),
)

# (table, column, value used to fill NULLs before NOT NULL)
_NOT_NULL = (
    ("monitor_runs", "credits_charged", "0"),
    ("monitors", "filters", "'{}'::json"),
    ("monitors", "updated_at", "now()"),
    ("organizations", "images_generated_today", "0"),
    ("organizations", "videos_generated_today", "0"),
    ("organizations", "images_trial_total", "0"),
    ("playbooks", "created_at", "now()"),
    ("playbooks", "updated_at", "now()"),
    ("support_ticket_replies", "created_at", "now()"),
    ("support_tickets", "created_at", "now()"),
    ("support_tickets", "updated_at", "now()"),
)

_CASCADE_FKS = (
    ("scout_leads", "job_id", "scout_jobs"),
    ("scout_maps_leads", "job_id", "scout_maps_jobs"),
)


def _column(conn, table, column):
    return conn.execute(
        text(
            "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).mappings().first()


def upgrade() -> None:
    conn = op.get_bind()

    for table, column in _TIMESTAMPTZ:
        col = _column(conn, table, column)
        if col and col["data_type"] == "timestamp without time zone":
            op.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE timestamp with time zone '
                f'USING "{column}" AT TIME ZONE ' + "'UTC'"
            )

    col = _column(conn, "monitor_runs", "credits_charged")
    if col and col["data_type"] in ("character varying", "text"):
        op.execute("ALTER TABLE monitor_runs ALTER COLUMN credits_charged DROP DEFAULT")
        op.execute(
            "ALTER TABLE monitor_runs ALTER COLUMN credits_charged TYPE double precision "
            "USING NULLIF(credits_charged, '')::double precision"
        )

    col = _column(conn, "scrape_jobs", "entity_profile")
    if col and col["data_type"] == "jsonb":
        op.execute("ALTER TABLE scrape_jobs ALTER COLUMN entity_profile TYPE json USING entity_profile::json")

    for table, column, default in _MISSING_DEFAULTS:
        col = _column(conn, table, column)
        if col and col["column_default"] is None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT {default}')

    for table, column, fill in _NOT_NULL:
        col = _column(conn, table, column)
        if col and col["is_nullable"] == "YES":
            op.execute(f'UPDATE "{table}" SET "{column}" = {fill} WHERE "{column}" IS NULL')
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET NOT NULL')

    for table, column, parent in _CASCADE_FKS:
        row = conn.execute(
            text(
                "SELECT con.conname, con.confdeltype FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey) "
                "WHERE con.contype = 'f' AND rel.relname = :t AND att.attname = :c "
                "AND rel.relnamespace = current_schema()::regnamespace"
            ),
            {"t": table, "c": column},
        ).mappings().first()
        if row and row["confdeltype"] != "c":
            op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{row["conname"]}"')
            op.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{row["conname"]}" FOREIGN KEY ("{column}") '
                f'REFERENCES "{parent}" (id) ON DELETE CASCADE'
            )


def downgrade() -> None:
    pass
