"""Monthly per-provider record counter (Metapi bills records).

Additive only: one new table without tenant data (one row per provider per
month), so no RLS; the API and worker roles may read and increment it.

Revision ID: e5a7c9d1f3b6
Revises: d3f5a7b9c1e4
"""

import sqlalchemy as sa
from alembic import op

revision = "e5a7c9d1f3b6"
down_revision = "d3f5a7b9c1e4"
branch_labels = None
depends_on = None

_TABLE = "provider_record_budget"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("provider", "period_start"),
    )
    for role in ("helix_app", "helix_worker"):
        op.execute(
            "DO $$ BEGIN "
            f"IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"GRANT SELECT, INSERT, UPDATE ON {_TABLE} TO {role}; END IF; "
            "END $$"
        )


def downgrade() -> None:
    op.drop_table(_TABLE)
