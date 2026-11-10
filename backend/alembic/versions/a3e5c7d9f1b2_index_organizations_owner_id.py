"""Index organizations.owner_id.

Every authenticated request looks up the caller's organizations by owner,
and the organizations RLS policy filters on owner_id. Without an index each
lookup is a sequential scan. Additive only: nothing is dropped or rewritten.

Revision ID: a3e5c7d9f1b2
Revises: d1f9c4a7b263
"""

from alembic import op

revision = "a3e5c7d9f1b2"
down_revision = "d1f9c4a7b263"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_organizations_owner_id",
        "organizations",
        ["owner_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_owner_id", table_name="organizations", if_exists=True)
