"""Permanent per-workspace ad archive (text + re-hosted media).

Additive only: one new table with tenant RLS like every other org-scoped
table. Nothing existing is dropped or rewritten.

Revision ID: c4e6a8b0d2f3
Revises: b7d2f4a6c8e1
"""

import sqlalchemy as sa
from alembic import op

revision = "c4e6a8b0d2f3"
down_revision = "b7d2f4a6c8e1"
branch_labels = None
depends_on = None

_TABLE = "ad_archive"
_EXPRESSION = (
    "(current_setting('helix.platform_admin', true) = '1' OR ("
    f"{_TABLE}.org_id = ANY "
    "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))))"
)


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("archive_key", sa.String(), nullable=False),
        sa.Column("creative_id", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("source_ad_id", sa.String(), nullable=True),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("format", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("body", sa.String(), nullable=True),
        sa.Column("cta", sa.String(), nullable=True),
        sa.Column("landing_domain", sa.String(), nullable=True),
        sa.Column("permalink", sa.String(), nullable=True),
        sa.Column("first_seen", sa.String(), nullable=True),
        sa.Column("last_seen", sa.String(), nullable=True),
        sa.Column("days_active", sa.Integer(), nullable=True),
        sa.Column("original_media_url", sa.String(), nullable=True),
        sa.Column("original_thumbnail_url", sa.String(), nullable=True),
        sa.Column("media_ref", sa.String(), nullable=True),
        sa.Column("thumbnail_ref", sa.String(), nullable=True),
        sa.Column("media_status", sa.String(), server_default="none", nullable=False),
        sa.Column("media_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "archive_key", name="uq_ad_archive_org_key"),
    )
    op.create_index(op.f("ix_ad_archive_org_id"), _TABLE, ["org_id"], unique=False)
    op.create_index(op.f("ix_ad_archive_creative_id"), _TABLE, ["creative_id"], unique=False)
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {_TABLE}_tenant_isolation ON {_TABLE} FOR ALL "
        f"USING {_EXPRESSION} WITH CHECK {_EXPRESSION}"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO helix_app; END IF; "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN "
        f"GRANT SELECT, INSERT, UPDATE ON {_TABLE} TO helix_worker; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_TABLE}_tenant_isolation ON {_TABLE}")
    op.drop_index(op.f("ix_ad_archive_creative_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_ad_archive_org_id"), table_name=_TABLE)
    op.drop_table(_TABLE)
