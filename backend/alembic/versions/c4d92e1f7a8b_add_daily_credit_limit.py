"""Add daily credit limit and daily usage tracking

Revision ID: c4d92e1f7a8b
Revises: 8873440dfb27
Create Date: 2026-08-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d92e1f7a8b'
down_revision: Union[str, Sequence[str], None] = '8873440dfb27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add daily_credit_limit to plans (nullable — None means unlimited)
    op.add_column('plans', sa.Column('daily_credit_limit', sa.Float(), nullable=True))

    # Add daily usage tracking to organizations
    op.add_column('organizations', sa.Column('daily_credits_used_today', sa.Float(), nullable=False, server_default='0'))
    op.add_column('organizations', sa.Column('daily_credits_reset_at', sa.DateTime(timezone=True), nullable=True))

    # Seed the trial plan with a daily limit: 25 credits / 7 days ≈ 3.57 → 3.5 (safe buffer)
    op.execute(
        "UPDATE plans SET daily_credit_limit = 3.5 WHERE id = 'plan_trial_default'"
    )


def downgrade() -> None:
    op.drop_column('organizations', 'daily_credits_reset_at')
    op.drop_column('organizations', 'daily_credits_used_today')
    op.drop_column('plans', 'daily_credit_limit')
