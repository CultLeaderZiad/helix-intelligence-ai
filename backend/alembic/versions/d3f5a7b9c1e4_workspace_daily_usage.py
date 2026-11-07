"""Per-workspace daily search and provider-call counters.

Additive only: one new table with the standard tenant RLS policy. Refunds do
not touch it, so caps on searches and provider calls hold even when a search
credit is refunded.

Revision ID: d3f5a7b9c1e4
Revises: b2d4f6a8c0e3
"""

import sqlalchemy as sa
from alembic import op

revision = "d3f5a7b9c1e4"
down_revision = "b2d4f6a8c0e3"
branch_labels = None
depends_on = None

_TABLE = "workspace_daily_usage"
_EXPRESSION = (
    "(current_setting('helix.platform_admin', true) = '1' OR ("
    f"{_TABLE}.org_id = ANY "
    "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))))"
)


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("searches", sa.Integer(), server_default="0", nullable=False),
        sa.Column("provider_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("day", "org_id"),
    )
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {_TABLE}_tenant_isolation ON {_TABLE} FOR ALL "
        f"USING {_EXPRESSION} WITH CHECK {_EXPRESSION}"
    )
    for role in ("helix_app", "helix_worker"):
        op.execute(
            "DO $$ BEGIN "
            f"IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"GRANT SELECT, INSERT, UPDATE ON {_TABLE} TO {role}; END IF; "
            "END $$"
        )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_TABLE}_tenant_isolation ON {_TABLE}")
    op.drop_table(_TABLE)
