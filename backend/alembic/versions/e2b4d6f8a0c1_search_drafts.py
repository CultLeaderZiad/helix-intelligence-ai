"""Saved Discover search drafts (per user, per workspace).

Additive only: one new table with tenant RLS matching every other
org-scoped table. Nothing existing is dropped or rewritten.

Revision ID: e2b4d6f8a0c1
Revises: a8c1e4b2d6f0
"""

import sqlalchemy as sa
from alembic import op

revision = "e2b4d6f8a0c1"
down_revision = "a8c1e4b2d6f0"
branch_labels = None
depends_on = None

_TABLE = "search_drafts"
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
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.String(length=2000), server_default="", nullable=False),
        sa.Column("filters", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_drafts_org_id"), _TABLE, ["org_id"], unique=False)
    op.create_index(op.f("ix_search_drafts_user_id"), _TABLE, ["user_id"], unique=False)
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
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_TABLE}_tenant_isolation ON {_TABLE}")
    op.drop_index(op.f("ix_search_drafts_user_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_search_drafts_org_id"), table_name=_TABLE)
    op.drop_table(_TABLE)
