"""Index monitor scheduling and latest-run lookups.

The scheduler claims rows with status = 'active' and next_run_at <= now().
The monitors list loads the newest run per monitor. Both were sequential
scans. Additive only.

Revision ID: d0e2f4a6b8c1
Revises: c9e1f3a5b7d0
"""

from alembic import op

revision = "d0e2f4a6b8c1"
down_revision = "c9e1f3a5b7d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_monitors_status_next_run_at",
        "monitors",
        ["status", "next_run_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_monitor_runs_monitor_started",
        "monitor_runs",
        ["monitor_id", "started_at"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_monitor_runs_monitor_started", table_name="monitor_runs", if_exists=True)
    op.drop_index("ix_monitors_status_next_run_at", table_name="monitors", if_exists=True)
