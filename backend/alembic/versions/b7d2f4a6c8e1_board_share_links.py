"""Guest board links (signed, read-only, revocable, expiring).

Additive only: one new table with tenant RLS matching every other
org-scoped table. Nothing existing is dropped or rewritten.

Revision ID: b7d2f4a6c8e1
Revises: a3e5c7d9f1b2
"""

import sqlalchemy as sa
from alembic import op

revision = "b7d2f4a6c8e1"
down_revision = "a3e5c7d9f1b2"
branch_labels = None
depends_on = None

_TABLE = "board_share_links"
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
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("collection_name", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_board_share_links_org_id"), _TABLE, ["org_id"], unique=False)
    op.create_index(op.f("ix_board_share_links_created_by"), _TABLE, ["created_by"], unique=False)
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {_TABLE}_tenant_isolation ON {_TABLE} FOR ALL "
        f"USING {_EXPRESSION} WITH CHECK {_EXPRESSION}"
    )
    # Default privileges already cover new tables; grant explicitly so a
    # database created without them still works for the restricted roles.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO helix_app; END IF; "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN "
        f"GRANT SELECT ON {_TABLE} TO helix_worker; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_TABLE}_tenant_isolation ON {_TABLE}")
    op.drop_index(op.f("ix_board_share_links_created_by"), table_name=_TABLE)
    op.drop_index(op.f("ix_board_share_links_org_id"), table_name=_TABLE)
    op.drop_table(_TABLE)
