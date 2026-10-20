"""Add a durable deadline to Discover jobs.

Revision ID: d1f9c4a7b263
Revises: b7e4c9a1d2f0
"""

from alembic import op
import sqlalchemy as sa

revision = "d1f9c4a7b263"
down_revision = "b7e4c9a1d2f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scrape_jobs", sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE scrape_jobs "
        "SET deadline_at = created_at + interval '600 seconds' "
        "WHERE deadline_at IS NULL"
    )
    op.create_index(
        "ix_scrape_jobs_active_deadline",
        "scrape_jobs",
        ["deadline_at"],
        postgresql_where=sa.text("status IN ('queued', 'running') AND deadline_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_scrape_jobs_active_deadline", table_name="scrape_jobs")
    op.drop_column("scrape_jobs", "deadline_at")
