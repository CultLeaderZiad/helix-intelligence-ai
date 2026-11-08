"""Per-plan usage limits (searches a day, monitors, monitor cadence).

Additive only: one nullable JSON column on plans (no tenant data, no RLS).
Empty or missing limits fall back to the global DISCOVER_* settings.

Revision ID: b8d0f2a4c6e9
Revises: a6c8e0f2b4d7
"""

import sqlalchemy as sa
from alembic import op

revision = "b8d0f2a4c6e9"
down_revision = "a6c8e0f2b4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("limits", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("plans", "limits")
