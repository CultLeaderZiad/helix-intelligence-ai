"""Drop the creatives.days_active default of 1.

Unknown run length must stay NULL. The server default turned an omitted or
explicit NULL into 1, so Discover, boards, and the archive reported a one-day
run. Existing rows are left as stored.

Revision ID: a8c1e4b2d6f0
Revises: c4e6a8b0d2f3
"""

import sqlalchemy as sa
from alembic import op

revision = "a8c1e4b2d6f0"
down_revision = "c4e6a8b0d2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "creatives",
        "days_active",
        existing_type=sa.Integer(),
        existing_nullable=True,
        existing_server_default="1",
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "creatives",
        "days_active",
        existing_type=sa.Integer(),
        existing_nullable=True,
        server_default="1",
    )
