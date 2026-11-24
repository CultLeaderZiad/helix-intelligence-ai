"""Alerts: Telegram chats and signed webhooks per workspace.

Additive only: one new tenant table with the same RLS policy and role grants
as every other org-scoped table. Old code ignores it.

Revision ID: d7f9b1c3e5a8
Revises: c6e8a0b2d4f7
"""
import sqlalchemy as sa
from alembic import op

revision = "d7f9b1c3e5a8"
down_revision = "c6e8a0b2d4f7"
branch_labels = None
depends_on = None

TABLE = "notification_channels"
EXPR = (
    "(current_setting('helix.platform_admin', true) = '1' OR ("
    f"{TABLE}.org_id = ANY "
    "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))))"
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("config_encrypted", sa.Text(), nullable=True),
        sa.Column("link_code_hash", sa.String(), nullable=True),
        sa.Column("link_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("link_code_hash"),
    )
    op.create_index(op.f("ix_notification_channels_org_id"), TABLE, ["org_id"], unique=False)
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {TABLE}_tenant_isolation ON {TABLE} FOR ALL USING {EXPR} WITH CHECK {EXPR}")
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO helix_app; END IF; "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN "
        f"GRANT SELECT, UPDATE ON {TABLE} TO helix_worker; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}")
    op.drop_index(op.f("ix_notification_channels_org_id"), table_name=TABLE)
    op.drop_table(TABLE)
