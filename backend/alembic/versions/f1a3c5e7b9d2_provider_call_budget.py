"""Global daily counter of paid provider calls.

Additive only: one new table. It holds no tenant data (one row per UTC day),
so it has no RLS; the API and worker roles may read and increment it.

Revision ID: f1a3c5e7b9d2
Revises: e2b4d6f8a0c1
"""

import sqlalchemy as sa
from alembic import op

revision = "f1a3c5e7b9d2"
down_revision = "e2b4d6f8a0c1"
branch_labels = None
depends_on = None

_TABLE = "provider_call_budget"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("day"),
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
