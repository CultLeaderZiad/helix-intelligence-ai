"""Revalidate alignment invariants for databases already stamped past b1.

Revision ID: b7e4c9a1d2f0
Revises: a9d4e6f8c2b0

The historical compatibility repair also needs to reach existing installs. Only
recover timestamps from stored job evidence; unknown history aborts this revision
atomically. No tenant assignment, row deletion, or guessed current time is used.
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e4c9a1d2f0"
down_revision = "a9d4e6f8c2b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE leadgen_jobs SET created_at = COALESCE(started_at, completed_at, heartbeat_at)
        WHERE created_at IS NULL
    """))
    conn.execute(sa.text("""
        UPDATE leadgen_leads AS lead SET created_at = job.created_at
        FROM leadgen_jobs AS job
        WHERE lead.job_id = job.id AND lead.created_at IS NULL
    """))
    for table, column in (
        ("leadgen_jobs", "created_at"),
        ("leadgen_leads", "created_at"),
        ("leadgen_worker_heartbeat", "updated_at"),
    ):
        if conn.execute(sa.text(f"SELECT 1 FROM {table} WHERE {column} IS NULL LIMIT 1")).first():
            raise RuntimeError(f"{table}.{column} contains NULL; repair from source evidence before retrying")
        op.alter_column(table, column, nullable=False, existing_type=sa.DateTime(timezone=True))

    # These are b1's historical supporting indexes, not its obsolete query-only
    # unique guard. The W3 canonical cache identity remains authoritative.
    for table, name, columns in (
        ("scrape_jobs", "ix_scrape_jobs_org_status_created", ["org_id", "status", "created_at"]),
        ("creatives", "ix_creatives_job_id", ["job_id"]),
        ("creatives", "ix_creatives_brand_id", ["brand_id"]),
        ("creatives", "ix_creatives_brand_name", ["brand_name"]),
        ("leadgen_leads", "ix_leadgen_leads_job_id", ["job_id"]),
    ):
        indexes = {index["name"] for index in sa.inspect(conn).get_indexes(table)}
        if name not in indexes:
            op.create_index(name, table, columns)
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_lower_email ON users (lower(email))"))


def downgrade() -> None:
    # Repair-only: every enforced invariant already belongs to the b1 schema.
    # Retain recovered source timestamps and historical constraints/indexes.
    # Dropping them would corrupt the target W3 shape rather than restore it.
    pass
