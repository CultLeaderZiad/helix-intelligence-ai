"""Persist complete discovery cache identity and replace query-only uniqueness.

Revision ID: a9d4e6f8c2b0
Revises: f3d9a7c2b1e4

Legacy filters/provider configuration are unknowable: leave identity NULL rather
than invent a backfill that could serve results for a different request.
"""
from alembic import op
import sqlalchemy as sa

revision = "a9d4e6f8c2b0"
down_revision = "f3d9a7c2b1e4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("scrape_jobs", sa.Column("cache_identity", sa.String(64), nullable=True))
    op.create_index("uq_scrape_jobs_active_identity", "scrape_jobs", ["org_id", "cache_identity"], unique=True,
                    postgresql_where=sa.text("status IN ('queued', 'running') AND cache_identity IS NOT NULL"))
    op.create_index("ix_scrape_jobs_cache_lookup", "scrape_jobs", ["org_id", "cache_identity", "status", "created_at"])
    op.drop_index("uq_scrape_jobs_active_query", table_name="scrape_jobs")


def downgrade():
    # Restore the old guard *before* removing the new one. If legitimate active
    # searches now share a query but not filters, this deliberately aborts the
    # transactional downgrade; an operator must drain them before retrying.
    # Never delete or rewrite jobs to force a rollback through.
    op.execute(sa.text("""
        CREATE UNIQUE INDEX uq_scrape_jobs_active_query
        ON scrape_jobs (org_id, lower(query))
        WHERE status IN ('queued', 'running')
    """))
    op.drop_index("ix_scrape_jobs_cache_lookup", table_name="scrape_jobs")
    op.drop_index("uq_scrape_jobs_active_identity", table_name="scrape_jobs")
    op.drop_column("scrape_jobs", "cache_identity")
