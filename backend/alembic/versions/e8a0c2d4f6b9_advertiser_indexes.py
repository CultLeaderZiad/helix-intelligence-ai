"""Advertiser page: indexes for its two hot queries.

Additive only (indexes). Revision ID: e8a0c2d4f6b9, Revises: d7f9b1c3e5a8
"""
from alembic import op

revision = "e8a0c2d4f6b9"
down_revision = "d7f9b1c3e5a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_monitor_creatives_creative_id", "monitor_creatives", ["creative_id"])
    op.create_index("ix_creatives_brand_landing", "creatives", ["brand_id", "landing_domain"])


def downgrade() -> None:
    op.drop_index("ix_creatives_brand_landing", table_name="creatives")
    op.drop_index("ix_monitor_creatives_creative_id", table_name="monitor_creatives")
