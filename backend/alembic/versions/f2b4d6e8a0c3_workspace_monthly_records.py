"""Count Metapi records per workspace per day, for the monthly workspace cap.

Additive: one integer column with a default of 0 on workspace_daily_usage.
Existing rows read as 0 records. The table's RLS policy and grants already
cover the new column. Downgrade drops it.

Revision ID: f2b4d6e8a0c3
Revises: e1a3c5e7f9b2
"""

import sqlalchemy as sa
from alembic import op

revision = "f2b4d6e8a0c3"
down_revision = "e1a3c5e7f9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_daily_usage",
        sa.Column("records", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("workspace_daily_usage", "records")
