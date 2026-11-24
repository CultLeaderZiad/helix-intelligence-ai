"""Helix Agent: cached generations per workspace.

Additive only: one tenant table with the standard RLS policy and grants.

Revision ID: b2d4f6a8c0e1
Revises: a1c3e5f7b9d2
"""
import sqlalchemy as sa
from alembic import op

revision = "b2d4f6a8c0e1"
down_revision = "a1c3e5f7b9d2"
branch_labels = None
depends_on = None

TABLE = "agent_generations"
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
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "kind", "input_hash", name="uq_agent_generations_org_kind_hash"),
    )
    op.create_index(op.f("ix_agent_generations_org_id"), TABLE, ["org_id"], unique=False)
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {TABLE}_tenant_isolation ON {TABLE} FOR ALL USING {EXPR} WITH CHECK {EXPR}")
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO helix_app; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}")
    op.drop_index(op.f("ix_agent_generations_org_id"), table_name=TABLE)
    op.drop_table(TABLE)
