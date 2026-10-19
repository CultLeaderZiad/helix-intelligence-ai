"""Complete production schema alignment (F01, F14, F63, F77)

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-10-02 02:00:00.000000

Reconciles all 14 missing tables, 24 missing columns, constraints, server defaults
and supporting indexes so that models and migrations describe identical databases without relying
on production create_all or startup ALTER loops.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_schema_cache(conn):
    insp = sa.inspect(conn)
    existing_tables = set(insp.get_table_names())
    existing_cols = {}
    existing_indexes = {}
    for t in existing_tables:
        try:
            existing_cols[t] = set(c['name'] for c in insp.get_columns(t))
        except Exception:
            existing_cols[t] = set()
        try:
            existing_indexes[t] = set(idx['name'] for idx in insp.get_indexes(t))
        except Exception:
            existing_indexes[t] = set()
    return existing_tables, existing_cols, existing_indexes


def _column_names(conn, table: str) -> set[str]:
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return set()
    return {col["name"] for col in insp.get_columns(table)}


def _index_names(conn, table: str) -> set[str]:
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return set()
    return {idx["name"] for idx in insp.get_indexes(table)}


def _ensure_index(conn, name: str, table: str, columns: list[str], unique: bool = False) -> None:
    if name in _index_names(conn, table):
        return
    op.create_index(name, table, columns, unique=unique)


def _json_not_jsonb(conn, table: str, column: str) -> None:
    """Models use JSON. A hand-built JSONB column fails alembic check."""
    row = conn.execute(
        sa.text(
            """
            SELECT udt_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).first()
    if row is None or row.udt_name != "jsonb":
        return
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE json USING {column}::json"))


def _drop_not_null_when_model_allows(conn, table: str, column: str) -> None:
    row = conn.execute(
        sa.text(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).first()
    if row is None or row.is_nullable == "YES":
        return
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"))


def _reconcile_api_keys(conn) -> None:
    if not sa.inspect(conn).has_table("api_keys"):
        return
    cols = _column_names(conn, "api_keys")
    if "prefix" not in cols and "key_prefix" in cols:
        op.execute(sa.text("ALTER TABLE api_keys RENAME COLUMN key_prefix TO prefix"))
    elif "prefix" in cols and "key_prefix" in cols:
        op.execute(sa.text("UPDATE api_keys SET prefix = COALESCE(prefix, key_prefix)"))
        op.execute(sa.text("ALTER TABLE api_keys DROP COLUMN key_prefix"))
    cols = _column_names(conn, "api_keys")
    if "prefix" not in cols:
        op.execute(sa.text("ALTER TABLE api_keys ADD COLUMN prefix VARCHAR"))
        op.execute(sa.text("UPDATE api_keys SET prefix = '' WHERE prefix IS NULL"))
        op.execute(sa.text("ALTER TABLE api_keys ALTER COLUMN prefix SET NOT NULL"))
    for extra in ("scopes", "expires_at"):
        if extra in cols:
            op.execute(sa.text(f"ALTER TABLE api_keys DROP COLUMN {extra}"))
    _ensure_index(conn, "ix_api_keys_key_hash", "api_keys", ["key_hash"])
    _ensure_index(conn, "ix_api_keys_org_id", "api_keys", ["org_id"])
    _ensure_index(conn, "ix_api_keys_user_id", "api_keys", ["user_id"])


def _reconcile_usage_logs(conn) -> None:
    if not sa.inspect(conn).has_table("usage_logs"):
        return
    cols = _column_names(conn, "usage_logs")
    if "metadata" in cols and "metadata_json" not in cols:
        op.execute(sa.text("ALTER TABLE usage_logs RENAME COLUMN metadata TO metadata_json"))
    elif "metadata" in cols and "metadata_json" in cols:
        op.execute(sa.text("UPDATE usage_logs SET metadata_json = COALESCE(metadata_json::jsonb, metadata::jsonb)::json"))
        op.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN metadata"))
    cols = _column_names(conn, "usage_logs")
    if "operation" not in cols:
        op.execute(sa.text("ALTER TABLE usage_logs ADD COLUMN operation VARCHAR"))
    if "feature_name" in cols:
        op.execute(
            sa.text(
                "UPDATE usage_logs SET operation = COALESCE(operation, feature_name, 'discover_search')"
            )
        )
        op.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN feature_name"))
    else:
        op.execute(sa.text("UPDATE usage_logs SET operation = COALESCE(operation, 'discover_search')"))
    op.execute(sa.text("ALTER TABLE usage_logs ALTER COLUMN operation SET DEFAULT 'discover_search'"))
    op.execute(sa.text("ALTER TABLE usage_logs ALTER COLUMN operation SET NOT NULL"))

    cols = _column_names(conn, "usage_logs")
    if "credits_deducted" not in cols:
        op.execute(sa.text("ALTER TABLE usage_logs ADD COLUMN credits_deducted DOUBLE PRECISION"))
    if "credits_charged" in _column_names(conn, "usage_logs"):
        op.execute(
            sa.text(
                "UPDATE usage_logs SET credits_deducted = COALESCE(credits_deducted, credits_charged)"
            )
        )
        op.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN credits_charged"))

    cols = _column_names(conn, "usage_logs")
    if "cost_usd" not in cols:
        op.execute(sa.text("ALTER TABLE usage_logs ADD COLUMN cost_usd DOUBLE PRECISION"))
    if "provider_cost_usd" in _column_names(conn, "usage_logs"):
        op.execute(
            sa.text("UPDATE usage_logs SET cost_usd = COALESCE(cost_usd, provider_cost_usd)")
        )
        op.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN provider_cost_usd"))

    additions = {
        "provider": "VARCHAR",
        "job_id": "VARCHAR",
        "units": "DOUBLE PRECISION",
        "tokens_used": "INTEGER",
        "requests_used": "INTEGER",
        "metadata_json": "JSON",
    }
    cols = _column_names(conn, "usage_logs")
    for name, ddl in additions.items():
        if name not in cols:
            op.execute(sa.text(f"ALTER TABLE usage_logs ADD COLUMN {name} {ddl}"))
    op.execute(sa.text("UPDATE usage_logs SET provider = 'legacy' WHERE provider IS NULL"))
    op.execute(sa.text("ALTER TABLE usage_logs ALTER COLUMN provider SET NOT NULL"))
    _json_not_jsonb(conn, "usage_logs", "metadata_json")
    for name, columns in (
        ("ix_usage_logs_created_at", ["created_at"]),
        ("ix_usage_logs_org_id", ["org_id"]),
        ("ix_usage_logs_user_id", ["user_id"]),
        ("ix_usage_logs_job_id", ["job_id"]),
        ("ix_usage_logs_provider", ["provider"]),
    ):
        _ensure_index(conn, name, "usage_logs", columns)


def _create_missing_billing_tables(conn) -> None:
    insp = sa.inspect(conn)
    if not insp.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=True),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("message", sa.String(), nullable=False),
            sa.Column("link", sa.String(), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
        op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
        op.create_index("ix_notifications_org_id", "notifications", ["org_id"])
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    if not insp.has_table("organization_invites"):
        op.create_table(
            "organization_invites",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("invited_by_user_id", sa.String(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_organization_invites_email", "organization_invites", ["email"])
        op.create_index("ix_organization_invites_org_id", "organization_invites", ["org_id"])
        op.create_index("ix_organization_invites_token", "organization_invites", ["token"], unique=True)
    if not insp.has_table("organization_members"):
        op.create_table(
            "organization_members",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_organization_members_org_id", "organization_members", ["org_id"])
        op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    if not insp.has_table("saved_creatives"):
        op.create_table(
            "saved_creatives",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=False),
            sa.Column("creative_id", sa.String(), nullable=False),
            sa.Column("collection_name", sa.String(), nullable=False),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["creative_id"], ["creatives.id"]),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_saved_creatives_collection_name", "saved_creatives", ["collection_name"])
        op.create_index("ix_saved_creatives_created_at", "saved_creatives", ["created_at"])
        op.create_index("ix_saved_creatives_creative_id", "saved_creatives", ["creative_id"])
        op.create_index("ix_saved_creatives_org_id", "saved_creatives", ["org_id"])
        op.create_index("ix_saved_creatives_user_id", "saved_creatives", ["user_id"])
    if not insp.has_table("external_api_usage"):
        op.create_table(
            "external_api_usage",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("query", sa.String(), nullable=True),
            sa.Column("max_records_requested", sa.Integer(), nullable=True),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def _reconcile_prod_drift(conn) -> None:
    _reconcile_api_keys(conn)
    _reconcile_usage_logs(conn)
    _create_missing_billing_tables(conn)
    _json_not_jsonb(conn, "plans", "feature_flags")
    _json_not_jsonb(conn, "organizations", "custom_feature_flags")
    for flag in ("is_suspended", "has_completed_onboarding", "is_banned"):
        _drop_not_null_when_model_allows(conn, "users", flag)


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables, existing_cols, existing_indexes = get_schema_cache(conn)

    def table_exists(*args) -> bool:
        tbl = args[-1]
        return tbl in existing_tables

    def column_exists(*args) -> bool:
        tbl, col = args[-2], args[-1]
        return col in existing_cols.get(tbl, set())

    def index_exists(*args) -> bool:
        tbl, idx = args[-2], args[-1]
        return idx in existing_indexes.get(tbl, set())



    # ---------------------------------------------------------
    # 1. Missing columns on existing tables
    # ---------------------------------------------------------

    # creatives
    if not column_exists(conn, 'creatives', 'is_estimated'):
        op.add_column('creatives', sa.Column('is_estimated', sa.Boolean(), nullable=True))
        existing_cols.setdefault('creatives', set()).add('is_estimated')
    if not column_exists(conn, 'creatives', 'data_source'):
        op.add_column('creatives', sa.Column('data_source', sa.String(), nullable=True))
        existing_cols.setdefault('creatives', set()).add('data_source')
    if not column_exists(conn, 'creatives', 'brand_name'):
        op.add_column('creatives', sa.Column('brand_name', sa.String(), nullable=True))
    if not column_exists(conn, 'creatives', 'media_url'):
        op.add_column('creatives', sa.Column('media_url', sa.String(), nullable=True))
    if not column_exists(conn, 'creatives', 'thumbnail_url'):
        op.add_column('creatives', sa.Column('thumbnail_url', sa.String(), nullable=True))

    # media_jobs
    if not column_exists(conn, 'media_jobs', 'failure_kind'):
        op.add_column('media_jobs', sa.Column('failure_kind', sa.String(), nullable=True))
    if not column_exists(conn, 'media_jobs', 'owner_boot_id'):
        op.add_column('media_jobs', sa.Column('owner_boot_id', sa.String(), nullable=True))
    if not column_exists(conn, 'media_jobs', 'heartbeat_at'):
        op.add_column('media_jobs', sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True))

    # organizations
    if not column_exists(conn, 'organizations', 'images_generated_today'):
        op.add_column('organizations', sa.Column('images_generated_today', sa.Float(), server_default='0.0', nullable=False))
    if not column_exists(conn, 'organizations', 'videos_generated_today'):
        op.add_column('organizations', sa.Column('videos_generated_today', sa.Float(), server_default='0.0', nullable=False))
    if not column_exists(conn, 'organizations', 'images_today_date'):
        op.add_column('organizations', sa.Column('images_today_date', sa.String(), server_default='', nullable=True))
    if not column_exists(conn, 'organizations', 'images_trial_total'):
        op.add_column('organizations', sa.Column('images_trial_total', sa.Float(), server_default='0.0', nullable=False))
    if not column_exists(conn, 'organizations', 'custom_feature_flags'):
        op.add_column('organizations', sa.Column('custom_feature_flags', sa.JSON(), server_default='{}', nullable=True))
    if not column_exists(conn, 'organizations', 'status'):
        op.add_column('organizations', sa.Column('status', sa.String(), server_default='active', nullable=False))

    # plans
    if not column_exists(conn, 'plans', 'daily_image_limit'):
        op.add_column('plans', sa.Column('daily_image_limit', sa.Integer(), server_default='5', nullable=True))
    if not column_exists(conn, 'plans', 'daily_video_limit'):
        op.add_column('plans', sa.Column('daily_video_limit', sa.Integer(), server_default='3', nullable=True))
    if not column_exists(conn, 'plans', 'price_monthly'):
        op.add_column('plans', sa.Column('price_monthly', sa.Float(), server_default='0.0', nullable=True))

    # scrape_jobs
    if not column_exists(conn, 'scrape_jobs', 'failure_kind'):
        op.add_column('scrape_jobs', sa.Column('failure_kind', sa.String(), nullable=True))
    if not column_exists(conn, 'scrape_jobs', 'owner_boot_id'):
        op.add_column('scrape_jobs', sa.Column('owner_boot_id', sa.String(), nullable=True))
    if not column_exists(conn, 'scrape_jobs', 'heartbeat_at'):
        op.add_column('scrape_jobs', sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True))
    if not column_exists(conn, 'scrape_jobs', 'entity_profile'):
        op.add_column('scrape_jobs', sa.Column('entity_profile', sa.JSON(), nullable=True))

    # users
    if not column_exists(conn, 'users', 'full_name'):
        op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    if not column_exists(conn, 'users', 'avatar_url'):
        op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    if not column_exists(conn, 'users', 'admin_permissions'):
        op.add_column('users', sa.Column('admin_permissions', sa.JSON(), server_default='{}', nullable=True))
    if not column_exists(conn, 'users', 'is_banned'):
        op.add_column('users', sa.Column('is_banned', sa.Boolean(), server_default='false', nullable=True))
    if not column_exists(conn, 'users', 'signup_metadata'):
        op.add_column('users', sa.Column('signup_metadata', sa.JSON(), server_default='{}', nullable=True))
    if not column_exists(conn, 'users', 'password_reset_token_hash'):
        op.add_column('users', sa.Column('password_reset_token_hash', sa.String(), nullable=True))
    if not column_exists(conn, 'users', 'password_reset_expires_at'):
        op.add_column('users', sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True))

    # ---------------------------------------------------------
    # 2. Reconcile Nullability from previous migrations (F77)
    # ---------------------------------------------------------
    if column_exists(conn, 'leadgen_jobs', 'created_at'):
        try:
            op.alter_column('leadgen_jobs', 'created_at', nullable=False, existing_type=sa.DateTime(timezone=True))
        except Exception:
            pass

    if column_exists(conn, 'leadgen_leads', 'created_at'):
        try:
            op.alter_column('leadgen_leads', 'created_at', nullable=False, existing_type=sa.DateTime(timezone=True))
        except Exception:
            pass

    if column_exists(conn, 'leadgen_worker_heartbeat', 'updated_at'):
        try:
            op.alter_column('leadgen_worker_heartbeat', 'updated_at', nullable=False, existing_type=sa.DateTime(timezone=True))
        except Exception:
            pass

    # Reconcile server defaults on existing tables
    if column_exists(conn, 'scrape_jobs', 'created_at'):
        try:
            op.alter_column('scrape_jobs', 'created_at', server_default=sa.func.now())
        except Exception:
            pass

    for col, default in [
        ('format', 'video'),
        ('days_active', '1'),
        ('variant_count', '1'),
        ('data_source', 'meta_official'),
    ]:
        if column_exists(conn, 'creatives', col):
            try:
                op.alter_column('creatives', col, server_default=default)
            except Exception:
                pass

    if column_exists(conn, 'creatives', 'is_estimated'):
        try:
            op.alter_column('creatives', 'is_estimated', server_default=sa.true())
        except Exception:
            pass

    if column_exists(conn, 'organizations', 'custom_feature_flags'):
        try:
            op.alter_column('organizations', 'custom_feature_flags', server_default='{}')
        except Exception:
            pass

    # ---------------------------------------------------------
    # 3. 14 Missing Tables
    # ---------------------------------------------------------

    # 3.1 app_updates
    if not table_exists(conn, 'app_updates'):
        op.create_table(
            'app_updates',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('level', sa.String(length=50), server_default='info', nullable=False),
            sa.Column('category', sa.String(length=100), server_default='General', nullable=True),
            sa.Column('is_published', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('show_as_banner', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('banner_dismissible', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('show_on_public', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('link_url', sa.String(length=500), nullable=True),
            sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 3.2 monitors
    if not table_exists(conn, 'monitors'):
        op.create_table(
            'monitors',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('query', sa.String(), nullable=False),
            sa.Column('filters', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('cadence', sa.String(), server_default='daily', nullable=False),
            sa.Column('status', sa.String(), server_default='active', nullable=False),
            sa.Column('paused_reason', sa.String(), nullable=True),
            sa.Column('notify_in_app', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('notify_email', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_job_id', sa.String(), nullable=True),
            sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False),
            sa.Column('baseline_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 3.3 monitor_runs
    if not table_exists(conn, 'monitor_runs'):
        op.create_table(
            'monitor_runs',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('monitor_id', sa.String(), sa.ForeignKey('monitors.id'), nullable=False),
            sa.Column('job_id', sa.String(), nullable=True),
            sa.Column('status', sa.String(), server_default='running', nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('creatives_seen', sa.Integer(), server_default='0', nullable=False),
            sa.Column('new_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('killed_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('changed_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('is_baseline', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('skipped_reason', sa.String(), nullable=True),
            sa.Column('error', sa.String(), nullable=True),
            sa.Column('credits_charged', sa.Float(), server_default='0.0', nullable=False),
        )

    # 3.4 monitor_creatives
    if not table_exists(conn, 'monitor_creatives'):
        op.create_table(
            'monitor_creatives',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('monitor_id', sa.String(), sa.ForeignKey('monitors.id'), nullable=False),
            sa.Column('identity_hash', sa.String(), nullable=False),
            sa.Column('content_hash', sa.String(), nullable=False),
            sa.Column('status', sa.String(), server_default='active', nullable=False),
            sa.Column('missed_runs', sa.Integer(), server_default='0', nullable=False),
            sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('creative_id', sa.String(), nullable=True),
            sa.Column('platform', sa.String(), nullable=True),
            sa.Column('format', sa.String(), nullable=True),
            sa.Column('headline', sa.String(), nullable=True),
            sa.Column('body', sa.String(), nullable=True),
            sa.Column('cta', sa.String(), nullable=True),
            sa.Column('landing_domain', sa.String(), nullable=True),
        )
        op.create_index('ix_monitor_creatives_identity', 'monitor_creatives', ['monitor_id', 'identity_hash'], unique=True)

    # 3.5 monitor_events
    if not table_exists(conn, 'monitor_events'):
        op.create_table(
            'monitor_events',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('monitor_id', sa.String(), sa.ForeignKey('monitors.id'), nullable=False),
            sa.Column('run_id', sa.String(), sa.ForeignKey('monitor_runs.id'), nullable=False),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('identity_hash', sa.String(), nullable=False),
            sa.Column('creative_id', sa.String(), nullable=True),
            sa.Column('headline', sa.String(), nullable=True),
            sa.Column('body', sa.String(), nullable=True),
            sa.Column('cta', sa.String(), nullable=True),
            sa.Column('platform', sa.String(), nullable=True),
            sa.Column('landing_domain', sa.String(), nullable=True),
            sa.Column('previous', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_monitor_events_monitor_created', 'monitor_events', ['monitor_id', 'created_at'])

    # 3.6 playbooks
    if not table_exists(conn, 'playbooks'):
        op.create_table(
            'playbooks',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('public_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('brand_name', sa.String(), nullable=False),
            sa.Column('query', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('summary', sa.String(), nullable=True),
            sa.Column('patterns', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('creatives', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('insights', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_playbooks_public_id', 'playbooks', ['public_id'], unique=True)
        op.create_index('ix_playbooks_brand_name', 'playbooks', ['brand_name'])
        op.create_index('ix_playbooks_org_id', 'playbooks', ['org_id'])
        op.create_index('ix_playbooks_user_id', 'playbooks', ['user_id'])
        op.create_index('ix_playbooks_created_at', 'playbooks', ['created_at'])

    # 3.7 scout_jobs
    if not table_exists(conn, 'scout_jobs'):
        op.create_table(
            'scout_jobs',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('status', sa.String(), server_default='queued', nullable=True),
            sa.Column('platforms', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('handles', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('enrich_emails', sa.Boolean(), server_default=sa.true(), nullable=True),
            sa.Column('target_category', sa.String(), nullable=True),
            sa.Column('generate_outreach', sa.Boolean(), server_default=sa.true(), nullable=True),
            sa.Column('stage', sa.String(), server_default='queued', nullable=True),
            sa.Column('stage_label', sa.String(), server_default='Job queued', nullable=True),
            sa.Column('stage_index', sa.Integer(), server_default='0', nullable=True),
            sa.Column('stages_total', sa.Integer(), server_default='4', nullable=True),
            sa.Column('logs', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('leads_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('elapsed_ms', sa.Integer(), server_default='0', nullable=True),
            sa.Column('credits_used', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('error_msg', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('owner_boot_id', sa.String(), nullable=True),
        )

    # 3.8 scout_leads
    if not table_exists(conn, 'scout_leads'):
        op.create_table(
            'scout_leads',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('job_id', sa.String(), sa.ForeignKey('scout_jobs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('platform', sa.String(), nullable=False),
            sa.Column('handle', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('phone', sa.String(), nullable=True),
            sa.Column('website', sa.String(), nullable=True),
            sa.Column('bio', sa.String(), nullable=True),
            sa.Column('followers', sa.Integer(), server_default='0', nullable=True),
            sa.Column('lead_score', sa.Integer(), server_default='0', nullable=True),
            sa.Column('profile_url', sa.String(), nullable=True),
            sa.Column('scrape_status', sa.String(), server_default='ok', nullable=True),
            sa.Column('account_type', sa.String(), nullable=True),
            sa.Column('priority_level', sa.String(), nullable=True),
            sa.Column('atlas', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('sources', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 3.9 scout_maps_jobs
    if not table_exists(conn, 'scout_maps_jobs'):
        op.create_table(
            'scout_maps_jobs',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('status', sa.String(), server_default='queued', nullable=True),
            sa.Column('keyword', sa.String(), nullable=False),
            sa.Column('city', sa.String(), nullable=False),
            sa.Column('lat', sa.Float(), nullable=True),
            sa.Column('lon', sa.Float(), nullable=True),
            sa.Column('depth', sa.Integer(), server_default='5', nullable=True),
            sa.Column('extract_emails', sa.Boolean(), server_default=sa.true(), nullable=True),
            sa.Column('pull_socials', sa.Boolean(), server_default=sa.false(), nullable=True),
            sa.Column('stage', sa.String(), server_default='queued', nullable=True),
            sa.Column('stage_label', sa.String(), server_default='Job queued', nullable=True),
            sa.Column('stage_index', sa.Integer(), server_default='0', nullable=True),
            sa.Column('stages_total', sa.Integer(), server_default='4', nullable=True),
            sa.Column('logs', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('results_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('elapsed_ms', sa.Integer(), server_default='0', nullable=True),
            sa.Column('credits_used', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('error_msg', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('owner_boot_id', sa.String(), nullable=True),
        )

    # 3.10 scout_maps_leads
    if not table_exists(conn, 'scout_maps_leads'):
        op.create_table(
            'scout_maps_leads',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('job_id', sa.String(), sa.ForeignKey('scout_maps_jobs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('phone', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('emails_found', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('website', sa.String(), nullable=True),
            sa.Column('category', sa.String(), nullable=True),
            sa.Column('address', sa.String(), nullable=True),
            sa.Column('city', sa.String(), nullable=True),
            sa.Column('rating', sa.Float(), nullable=True),
            sa.Column('reviews_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('instagram', sa.String(), nullable=True),
            sa.Column('facebook', sa.String(), nullable=True),
            sa.Column('linkedin', sa.String(), nullable=True),
            sa.Column('twitter', sa.String(), nullable=True),
            sa.Column('socials', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('metadata_raw', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 3.11 simulation_reports
    if not table_exists(conn, 'simulation_reports'):
        op.create_table(
            'simulation_reports',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('creative_id', sa.String(), sa.ForeignKey('creatives.id'), nullable=False),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data_source', sa.String(), server_default='simulated', nullable=False),
            sa.Column('is_estimated', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('model_version', sa.String(), nullable=True),
            sa.Column('assumptions', sa.JSON(), nullable=True),
            sa.Column('evidence_creative_ids', sa.JSON(), nullable=True),
            sa.Column('segment_reactions', sa.JSON(), nullable=True),
            sa.Column('recommended_angles', sa.JSON(), nullable=True),
            sa.Column('generated_at', sa.String(), nullable=True),
        )

    # 3.12 support_tickets
    if not table_exists(conn, 'support_tickets'):
        op.create_table(
            'support_tickets',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('type', sa.String(), server_default='feedback', nullable=False),
            sa.Column('subject', sa.String(), nullable=False),
            sa.Column('message', sa.String(), nullable=False),
            sa.Column('status', sa.String(), server_default='open', nullable=False),
            sa.Column('tag', sa.String(), nullable=True),
            sa.Column('context_data', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_support_tickets_created_at', 'support_tickets', ['created_at'])
        op.create_index('ix_support_tickets_org_id', 'support_tickets', ['org_id'])
        op.create_index('ix_support_tickets_user_id', 'support_tickets', ['user_id'])

    # 3.13 support_ticket_replies
    if not table_exists(conn, 'support_ticket_replies'):
        op.create_table(
            'support_ticket_replies',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('ticket_id', sa.String(), sa.ForeignKey('support_tickets.id'), nullable=False),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('message', sa.String(), nullable=False),
            sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_support_ticket_replies_created_at', 'support_ticket_replies', ['created_at'])
        op.create_index('ix_support_ticket_replies_ticket_id', 'support_ticket_replies', ['ticket_id'])
        op.create_index('ix_support_ticket_replies_user_id', 'support_ticket_replies', ['user_id'])

    # 3.14 workspace_provider_credentials
    if not table_exists(conn, 'workspace_provider_credentials'):
        op.create_table(
            'workspace_provider_credentials',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('provider', sa.String(), nullable=False),
            sa.Column('encrypted_secret', sa.String(), nullable=False),
            sa.Column('key_suffix', sa.String(), nullable=True),
            sa.Column('status', sa.String(), server_default='connected', nullable=True),
            sa.Column('credential_mode', sa.String(), server_default='managed', nullable=True),
            sa.Column('model', sa.String(), nullable=True),
            sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ---------------------------------------------------------
    # 3b. Production drift that the earlier revisions never saw.
    # A database stamped at c4d92e1f7a8b can still be missing the
    # billing tables, and can still have the pre-model api_keys and
    # usage_logs columns. Converge those to the models. Rows are kept.
    # ---------------------------------------------------------
    _reconcile_prod_drift(conn)

    # ---------------------------------------------------------
    # 4. Supporting Indexes (F63) & Dedup Guard Index
    # ---------------------------------------------------------
    # 4.1 Dedup Guard Unique Index on scrape_jobs
    try:
        op.execute(sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_scrape_jobs_active_query
            ON scrape_jobs (org_id, lower(query))
            WHERE status IN ('queued', 'running')
        """))
    except Exception:
        pass

    # 4.2 Supporting query performance indexes (F63)
    if not index_exists(conn, 'scrape_jobs', 'ix_scrape_jobs_org_status_created'):
        try:
            op.create_index('ix_scrape_jobs_org_status_created', 'scrape_jobs', ['org_id', 'status', 'created_at'])
        except Exception:
            pass

    if not index_exists(conn, 'creatives', 'ix_creatives_job_id'):
        try:
            op.create_index('ix_creatives_job_id', 'creatives', ['job_id'])
        except Exception:
            pass

    if not index_exists(conn, 'creatives', 'ix_creatives_brand_id'):
        try:
            op.create_index('ix_creatives_brand_id', 'creatives', ['brand_id'])
        except Exception:
            pass

    if not index_exists(conn, 'creatives', 'ix_creatives_brand_name'):
        try:
            op.create_index('ix_creatives_brand_name', 'creatives', ['brand_name'])
        except Exception:
            pass

    if table_exists(conn, 'leadgen_leads') and not index_exists(conn, 'leadgen_leads', 'ix_leadgen_leads_job_id'):
        try:
            op.create_index('ix_leadgen_leads_job_id', 'leadgen_leads', ['job_id'])
        except Exception:
            pass

    try:
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_lower_email ON users (lower(email))"))
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()

    try:
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_lower_email"))
        op.drop_index('ix_leadgen_leads_job_id', table_name='leadgen_leads')
        op.drop_index('ix_creatives_brand_id', table_name='creatives')
        op.drop_index('ix_creatives_job_id', table_name='creatives')
        op.drop_index('ix_scrape_jobs_org_status_created', table_name='scrape_jobs')
        op.drop_index('uq_scrape_jobs_active_query', table_name='scrape_jobs')
    except Exception:
        pass

    # Drop tables in reverse FK order
    for tbl in [
        'workspace_provider_credentials',
        'support_ticket_replies',
        'support_tickets',
        'simulation_reports',
        'scout_maps_leads',
        'scout_maps_jobs',
        'scout_leads',
        'scout_jobs',
        'playbooks',
        'monitor_events',
        'monitor_creatives',
        'monitor_runs',
        'monitors',
        'app_updates',
    ]:
        if table_exists(conn, tbl):
            op.drop_table(tbl)

    # Columns dropped on downgrade
    for col in ['brand_name', 'media_url', 'thumbnail_url']:
        if column_exists(conn, 'creatives', col):
            op.drop_column('creatives', col)

    for col in ['failure_kind', 'owner_boot_id', 'heartbeat_at']:
        if column_exists(conn, 'media_jobs', col):
            op.drop_column('media_jobs', col)

    for col in ['images_generated_today', 'videos_generated_today', 'images_today_date', 'images_trial_total', 'custom_feature_flags', 'status']:
        if column_exists(conn, 'organizations', col):
            op.drop_column('organizations', col)

    for col in ['daily_image_limit', 'daily_video_limit', 'price_monthly']:
        if column_exists(conn, 'plans', col):
            op.drop_column('plans', col)

    for col in ['failure_kind', 'owner_boot_id', 'heartbeat_at', 'entity_profile']:
        if column_exists(conn, 'scrape_jobs', col):
            op.drop_column('scrape_jobs', col)

    for col in ['full_name', 'avatar_url', 'admin_permissions', 'is_banned', 'signup_metadata', 'password_reset_token_hash', 'password_reset_expires_at']:
        if column_exists(conn, 'users', col):
            op.drop_column('users', col)
