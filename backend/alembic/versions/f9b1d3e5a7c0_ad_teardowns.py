"""AI teardown cache, shared across workspaces (public ad copy only).

Additive only. No tenant RLS: the table holds no workspace data; usage per
workspace is recorded in usage_logs (which is tenant-scoped).

Revision ID: f9b1d3e5a7c0
Revises: e8a0c2d4f6b9
"""
import sqlalchemy as sa
from alembic import op

revision = "f9b1d3e5a7c0"
down_revision = "e8a0c2d4f6b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_teardowns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        "GRANT SELECT, INSERT ON ad_teardowns TO helix_app; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.drop_table("ad_teardowns")
