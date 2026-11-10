"""W2 durable work items and creative source provenance.

Revision ID: c2a4e8b1d907
Revises: f8b3c4d5e6a7
Create Date: 2026-10-18 22:10:00.000000

Forward-only. Does not rewrite an already-deployed revision.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a4e8b1d907"
down_revision: Union[str, Sequence[str], None] = "f8b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _policy(table: str) -> None:
    expression = """(
        current_setting('helix.enforce', true) IS DISTINCT FROM '1'
        OR current_setting('helix.platform_admin', true) = '1'
        OR org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )"""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_tenant_isolation ON {table} "
        f"FOR ALL USING {expression} WITH CHECK {expression}"
    )


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lease_owner", sa.String(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_operation_id", sa.String(), nullable=True),
        sa.Column("provider_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested", sa.String(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "kind", "idempotency_key", name="uq_work_items_org_kind_key"),
    )
    op.create_index("ix_work_items_org_id", "work_items", ["org_id"])
    op.create_index("ix_work_items_job_id", "work_items", ["job_id"])
    _policy("work_items")

    op.add_column("creatives", sa.Column("source_ad_id", sa.String(), nullable=True))
    op.add_column("creatives", sa.Column("permalink", sa.String(), nullable=True))
    op.add_column("creatives", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("creatives", sa.Column("provenance_json", sa.JSON(), nullable=True))
    op.add_column("creatives", sa.Column("score_basis", sa.String(), nullable=True))
    op.add_column("creatives", sa.Column("score_scale", sa.String(), nullable=True))
    op.add_column("creatives", sa.Column("heuristic_version", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("creatives", "heuristic_version")
    op.drop_column("creatives", "score_scale")
    op.drop_column("creatives", "score_basis")
    op.drop_column("creatives", "provenance_json")
    op.drop_column("creatives", "fetched_at")
    op.drop_column("creatives", "permalink")
    op.drop_column("creatives", "source_ad_id")
    op.execute("DROP POLICY IF EXISTS work_items_tenant_isolation ON work_items")
    op.execute("ALTER TABLE work_items NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE work_items DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_work_items_job_id", table_name="work_items")
    op.drop_index("ix_work_items_org_id", table_name="work_items")
    op.drop_table("work_items")
