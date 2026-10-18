"""Null unmeasured lift and review counts, and grant the restricted roles.

Revision ID: d4f6a8c0e2b1
Revises: c2a4e8b1d907
Create Date: 2026-10-18 22:40:00.000000

Forward-only. Does not rewrite an already-deployed revision.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f6a8c0e2b1"
down_revision: Union[str, Sequence[str], None] = "c2a4e8b1d907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("patterns", "lift_index", existing_type=sa.Float(), nullable=True)
    op.execute("UPDATE patterns SET lift_index = NULL WHERE lift_index = 0")
    op.alter_column(
        "scout_maps_leads",
        "reviews_count",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
    op.execute("GRANT USAGE ON SCHEMA public TO helix_app, helix_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO helix_app, helix_worker"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO helix_app, helix_worker")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO helix_app, helix_worker"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO helix_app, helix_worker"
    )


def downgrade() -> None:
    op.execute("UPDATE patterns SET lift_index = 0 WHERE lift_index IS NULL")
    op.alter_column("patterns", "lift_index", existing_type=sa.Float(), nullable=False)
    op.execute("UPDATE scout_maps_leads SET reviews_count = 0 WHERE reviews_count IS NULL")
    op.alter_column(
        "scout_maps_leads",
        "reviews_count",
        existing_type=sa.Integer(),
        nullable=True,
        server_default="0",
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM helix_app, helix_worker"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM helix_app, helix_worker"
    )
