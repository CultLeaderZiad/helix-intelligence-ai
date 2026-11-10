"""Public pricing details per plan (edited by full admins).

Additive only: one nullable JSON column. Plans carry no tenant data and have
no RLS; the public pricing endpoint reads only plans marked listed.

Revision ID: a6c8e0f2b4d7
Revises: e5a7c9d1f3b6
"""

import sqlalchemy as sa
from alembic import op

revision = "a6c8e0f2b4d7"
down_revision = "e5a7c9d1f3b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("pricing", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("plans", "pricing")
