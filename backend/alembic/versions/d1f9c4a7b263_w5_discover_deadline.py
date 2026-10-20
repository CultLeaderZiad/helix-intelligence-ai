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


def _set_work_item_policies(*, include_running: bool) -> None:
    owner = "lease_owner = current_setting('helix.worker_id', true)"
    worker = (
        "(current_user = 'helix_worker' OR pg_has_role(current_user, 'helix_worker', 'MEMBER')) "
        "AND current_setting('helix.worker_claim', true) = '1'"
    )
    maintenance = (
        "(current_user = 'helix_worker' OR pg_has_role(current_user, 'helix_worker', 'MEMBER')) "
        "AND current_setting('helix.maintenance', true) = '1'"
    )
    active = "('leased', 'running')" if include_running else "('leased')"
    due = "(status = 'queued' AND available_at <= now() AND cancel_requested IS NULL)"

    for name in (
        "work_items_worker_claim_select",
        "work_items_worker_claim_update",
        "work_items_maintenance_queue_select",
        "work_items_maintenance_expired_select",
        "work_items_maintenance_expired_update",
    ):
        op.execute(f"DROP POLICY IF EXISTS {name} ON work_items")

    op.execute(
        "CREATE POLICY work_items_worker_claim_select ON work_items FOR SELECT "
        f"USING ({worker} AND ({due} OR (status IN {active} AND {owner})))"
    )
    op.execute(
        "CREATE POLICY work_items_worker_claim_update ON work_items FOR UPDATE "
        f"USING ({worker} AND ({due} OR (status IN {active} AND {owner}))) "
        f"WITH CHECK ({worker} AND ((status IN {active} AND {owner}) "
        "OR (status IN ('queued', 'dead', 'canceled', 'succeeded') "
        "AND lease_owner IS NULL AND lease_until IS NULL)))"
    )
    queue_states = "('queued', 'leased', 'running')" if include_running else "('queued', 'leased')"
    op.execute(
        "CREATE POLICY work_items_maintenance_queue_select ON work_items FOR SELECT "
        f"USING ({maintenance} AND status IN {queue_states})"
    )
    expired = (
        f"{maintenance} AND status IN {active} "
        "AND lease_until IS NOT NULL AND lease_until < now()"
    )
    op.execute(
        "CREATE POLICY work_items_maintenance_expired_select ON work_items FOR SELECT "
        f"USING ({expired})"
    )
    op.execute(
        "CREATE POLICY work_items_maintenance_expired_update ON work_items FOR UPDATE "
        f"USING ({expired}) WITH CHECK ({maintenance} "
        "AND status IN ('queued', 'dead', 'canceled') "
        "AND lease_owner IS NULL AND lease_until IS NULL)"
    )


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
    _set_work_item_policies(include_running=True)


def downgrade() -> None:
    _set_work_item_policies(include_running=False)
    op.drop_index("ix_scrape_jobs_active_deadline", table_name="scrape_jobs")
    op.drop_column("scrape_jobs", "deadline_at")
