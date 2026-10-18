"""Durable unique Neon auth webhook event ids.

Revision ID: d5e8c0a1b2f3
Revises: b1c2d3e4f5a6
Create Date: 2026-10-18 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e8c0a1b2f3"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("webhook_events", sa.Column("event_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_webhook_events_provider_event_id",
        "webhook_events",
        ["provider", "event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_webhook_events_provider_event_id", "webhook_events", type_="unique")
    op.drop_column("webhook_events", "event_id")
