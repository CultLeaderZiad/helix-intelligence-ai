"""Make tenant RLS fail closed without an organization context.

Revision ID: f3d9a7c2b1e4
Revises: e8c3b5d7a2f4
Create Date: 2026-10-19 00:10:00.000000

This forward migration replaces the fail-open tenant policies without
rewriting any deployed revision. Cross-tenant queue and maintenance access is
limited to the specific rows and operations those background paths require.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f3d9a7c2b1e4"
down_revision: Union[str, Sequence[str], None] = "e8c3b5d7a2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DIRECT_ORG_TABLES = (
    "scrape_jobs",
    "external_api_usage",
    "leadgen_jobs",
    "leadgen_leads",
    "media_jobs",
    "monitors",
    "notifications",
    "organization_invites",
    "playbooks",
    "saved_creatives",
    "scout_jobs",
    "scout_leads",
    "scout_maps_jobs",
    "scout_maps_leads",
    "simulation_reports",
    "support_tickets",
    "usage_logs",
    "workspace_provider_credentials",
    "patterns",
    "operation_idempotency",
    "credit_reservations",
    "credit_ledger",
    "access_requests",
    "organization_access_grants",
    "work_items",
)

_INDIRECT_PREDICATES = {
    "creatives": """EXISTS (
        SELECT 1 FROM scrape_jobs j
        WHERE j.id = creatives.job_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "ai_insights": """EXISTS (
        SELECT 1 FROM creatives c
        JOIN scrape_jobs j ON j.id = c.job_id
        WHERE c.id = ai_insights.creative_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "creative_scores": """EXISTS (
        SELECT 1 FROM creatives c
        JOIN scrape_jobs j ON j.id = c.job_id
        WHERE c.id = creative_scores.creative_id
          AND j.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_runs": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_runs.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_creatives": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_creatives.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "monitor_events": """EXISTS (
        SELECT 1 FROM monitors m
        WHERE m.id = monitor_events.monitor_id
          AND m.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
    "support_ticket_replies": """EXISTS (
        SELECT 1 FROM support_tickets t
        WHERE t.id = support_ticket_replies.ticket_id
          AND t.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
    )""",
}

_ROLE_CHECK = (
    "(current_user = 'helix_worker' "
    "OR pg_has_role(current_user, 'helix_worker', 'MEMBER'))"
)
_APP_OR_WORKER_CHECK = (
    "((current_user = 'helix_app' OR pg_has_role(current_user, 'helix_app', 'MEMBER')) "
    "OR (current_user = 'helix_worker' "
    "OR pg_has_role(current_user, 'helix_worker', 'MEMBER')))"
)


def _org_predicate(table: str) -> str:
    return (
        f"{table}.org_id = ANY "
        "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))"
    )


def _table_predicates() -> dict[str, str]:
    predicates = {table: _org_predicate(table) for table in _DIRECT_ORG_TABLES}
    predicates["organizations"] = """(
        organizations.id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
        OR organizations.owner_id = current_setting('helix.user_id', true)
    )"""
    predicates["organization_members"] = """(
        organization_members.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))
        OR organization_members.user_id = current_setting('helix.user_id', true)
    )"""
    predicates.update(_INDIRECT_PREDICATES)
    return predicates


def _new_expression(predicate: str) -> str:
    return f"(current_setting('helix.platform_admin', true) = '1' OR ({predicate}))"


def _old_expression(predicate: str) -> str:
    return (
        "(current_setting('helix.enforce', true) IS DISTINCT FROM '1' "
        "OR current_setting('helix.platform_admin', true) = '1' "
        f"OR ({predicate}))"
    )


def _replace_policy(table: str, predicate: str, expression_builder) -> None:
    policy = f"{table}_tenant_isolation"
    expression = expression_builder(predicate)
    op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(
        f"CREATE POLICY {policy} ON {table} FOR ALL "
        f"USING {expression} WITH CHECK {expression}"
    )


def _create_worker_queue_policies() -> None:
    worker = f"{_ROLE_CHECK} AND current_setting('helix.worker_claim', true) = '1'"
    owner_match = "lease_owner = current_setting('helix.worker_id', true)"
    due_item = "(status = 'queued' AND available_at <= now() AND cancel_requested IS NULL)"
    claim_select = f"({worker} AND ({due_item} OR (status = 'leased' AND {owner_match})))"
    op.execute(
        "CREATE POLICY work_items_worker_claim_select ON work_items FOR SELECT "
        f"USING {claim_select}"
    )
    op.execute(
        "CREATE POLICY work_items_worker_claim_update ON work_items FOR UPDATE "
        f"USING ({worker} AND ({due_item} OR (status = 'leased' AND {owner_match}))) "
        f"WITH CHECK ({worker} AND ((status = 'leased' AND {owner_match}) "
        "OR (status IN ('queued', 'dead', 'canceled', 'succeeded') "
        "AND lease_owner IS NULL AND lease_until IS NULL)))"
    )

    # The standalone Scrapling loop predates the work-item outbox. It may
    # atomically lease only queued LeadGen jobs; it still must bind org scope
    # before reading job details or touching lead rows.
    leadgen_worker = (
        f"{_ROLE_CHECK} AND current_setting('helix.worker_claim', true) = '1'"
    )
    claimed_id = "current_setting('helix.worker_id', true)"
    op.execute(
        "CREATE POLICY leadgen_jobs_worker_claim_select ON leadgen_jobs FOR SELECT "
        f"USING ({leadgen_worker} AND (status = 'queued' "
        f"OR (status = 'running' AND owner_boot_id = {claimed_id})))"
    )
    op.execute(
        "CREATE POLICY leadgen_jobs_worker_claim_update ON leadgen_jobs FOR UPDATE "
        f"USING ({leadgen_worker} AND status = 'queued') "
        f"WITH CHECK ({leadgen_worker} AND status = 'running' AND owner_boot_id = {claimed_id})"
    )


def _create_maintenance_policies() -> None:
    maintenance = (
        f"{_APP_OR_WORKER_CHECK} AND current_setting('helix.maintenance', true) = '1'"
    )
    stale = (
        "COALESCE(heartbeat_at, created_at) < now() - interval '120 seconds' "
        "AND (owner_boot_id IS NULL OR owner_boot_id <> "
        "current_setting('helix.maintenance_boot', true))"
    )
    stale_statuses = {
        "scrape_jobs": "status IN ('queued', 'running')",
        "media_jobs": "status IN ('pending', 'running', 'processing', 'in_progress')",
        "scout_jobs": "status IN ('queued', 'running')",
        "scout_maps_jobs": "status IN ('queued', 'running')",
        "leadgen_jobs": "status IN ('queued', 'running')",
    }
    for table, status_predicate in stale_statuses.items():
        predicate = f"{maintenance} AND {status_predicate} AND {stale}"
        op.execute(
            f"CREATE POLICY {table}_maintenance_select ON {table} FOR SELECT USING ({predicate})"
        )
        op.execute(
            f"CREATE POLICY {table}_maintenance_update ON {table} FOR UPDATE "
            f"USING ({predicate}) WITH CHECK ({maintenance} AND status = 'failed')"
        )

    # Failed scrape rows and their matching usage ledger entries are the only
    # extra rows the restart reconciler may inspect for idempotent refunds.
    failed_scrape = f"{maintenance} AND status = 'failed'"
    op.execute(
        "CREATE POLICY scrape_jobs_maintenance_failed_select ON scrape_jobs "
        f"FOR SELECT USING ({failed_scrape})"
    )
    op.execute(
        "CREATE POLICY scrape_jobs_maintenance_monitor_select ON scrape_jobs FOR SELECT "
        f"USING ({maintenance} AND EXISTS (SELECT 1 FROM monitor_runs mr "
        "WHERE mr.job_id = scrape_jobs.id AND mr.status = 'running' "
        "AND mr.started_at < now() - interval '120 seconds'))"
    )
    op.execute(
        "CREATE POLICY usage_logs_maintenance_failed_jobs_select ON usage_logs FOR SELECT "
        f"USING ({maintenance} AND job_id IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM scrape_jobs sj WHERE sj.id = usage_logs.job_id AND sj.status = 'failed'))"
    )

    # The reconciler only reads queue state to avoid failing a job that still
    # has runnable work; it cannot update work items through this policy.
    op.execute(
        "CREATE POLICY work_items_maintenance_queue_select ON work_items FOR SELECT "
        f"USING ({maintenance} AND status IN ('queued', 'leased'))"
    )

    # Monitor cleanup only reads runs stale beyond the same fixed safety
    # window, and only their parent monitor for its org id and notification.
    stale_run = f"{maintenance} AND status = 'running' AND started_at < now() - interval '120 seconds'"
    op.execute(
        "CREATE POLICY monitor_runs_maintenance_select ON monitor_runs FOR SELECT "
        f"USING ({stale_run})"
    )
    op.execute(
        "CREATE POLICY monitor_runs_maintenance_update ON monitor_runs FOR UPDATE "
        f"USING ({stale_run}) WITH CHECK ({maintenance} AND status = 'failed')"
    )
    op.execute(
        "CREATE POLICY monitors_maintenance_parent_select ON monitors FOR SELECT "
        f"USING ({maintenance} AND id = current_setting('helix.maintenance_monitor_id', true))"
    )

    # A scheduler may claim only due active monitors and advance their next
    # run timestamp; it cannot use this policy for ordinary monitor reads.
    scheduler = (
        "((current_user = 'helix_app' OR pg_has_role(current_user, 'helix_app', 'MEMBER')) "
        "AND current_setting('helix.monitor_claim', true) = '1')"
    )
    due_monitor = f"{scheduler} AND status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= now()"
    scheduler_claimed = (
        f"{scheduler} AND status = 'active' AND next_run_at > now() "
        "AND last_run_at >= now() - interval '1 minute'"
    )
    op.execute(
        "CREATE POLICY monitors_scheduler_select ON monitors FOR SELECT "
        f"USING (({due_monitor}) OR ({scheduler_claimed}))"
    )
    op.execute(
        "CREATE POLICY monitors_scheduler_update ON monitors FOR UPDATE "
        f"USING ({due_monitor}) WITH CHECK ("
        f"{scheduler} AND status = 'active' AND next_run_at > now() "
        "AND last_run_at >= now() - interval '1 minute')"
    )

    # Expired leases may be requeued or dead-lettered, but the worker/app
    # cannot use this policy to inspect or alter live leases.
    expired_item = (
        f"{maintenance} AND status = 'leased' AND lease_until IS NOT NULL AND lease_until < now()"
    )
    op.execute(
        "CREATE POLICY work_items_maintenance_expired_select ON work_items FOR SELECT "
        f"USING ({expired_item})"
    )
    op.execute(
        "CREATE POLICY work_items_maintenance_expired_update ON work_items FOR UPDATE "
        f"USING ({expired_item}) WITH CHECK ("
        f"{maintenance} AND status IN ('queued', 'dead') "
        "AND lease_owner IS NULL AND lease_until IS NULL)"
    )


def upgrade() -> None:
    for table, predicate in _table_predicates().items():
        _replace_policy(table, predicate, _new_expression)
        # Keep RLS enabled, but let the table owner/migration role retain its
        # normal PostgreSQL owner access. Restricted app/worker roles remain
        # subject to the fail-closed policies.
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")

    _create_worker_queue_policies()
    _create_maintenance_policies()
    op.execute("ALTER ROLE helix_app SET helix.enforce = '1'")
    op.execute("ALTER ROLE helix_worker SET helix.enforce = '1'")


def downgrade() -> None:
    for policy, table in (
        ("work_items_worker_claim_select", "work_items"),
        ("work_items_worker_claim_update", "work_items"),
        ("leadgen_jobs_worker_claim_select", "leadgen_jobs"),
        ("leadgen_jobs_worker_claim_update", "leadgen_jobs"),
        ("scrape_jobs_maintenance_select", "scrape_jobs"),
        ("scrape_jobs_maintenance_update", "scrape_jobs"),
        ("media_jobs_maintenance_select", "media_jobs"),
        ("media_jobs_maintenance_update", "media_jobs"),
        ("scout_jobs_maintenance_select", "scout_jobs"),
        ("scout_jobs_maintenance_update", "scout_jobs"),
        ("scout_maps_jobs_maintenance_select", "scout_maps_jobs"),
        ("scout_maps_jobs_maintenance_update", "scout_maps_jobs"),
        ("leadgen_jobs_maintenance_select", "leadgen_jobs"),
        ("leadgen_jobs_maintenance_update", "leadgen_jobs"),
        ("scrape_jobs_maintenance_failed_select", "scrape_jobs"),
        ("scrape_jobs_maintenance_monitor_select", "scrape_jobs"),
        ("usage_logs_maintenance_failed_jobs_select", "usage_logs"),
        ("work_items_maintenance_queue_select", "work_items"),
        ("monitor_runs_maintenance_select", "monitor_runs"),
        ("monitor_runs_maintenance_update", "monitor_runs"),
        ("monitors_maintenance_parent_select", "monitors"),
        ("monitors_scheduler_select", "monitors"),
        ("monitors_scheduler_update", "monitors"),
        ("work_items_maintenance_expired_select", "work_items"),
        ("work_items_maintenance_expired_update", "work_items"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")

    # Restore the original forced-RLS state and the original expressions.
    for table, predicate in _table_predicates().items():
        _replace_policy(table, predicate, _old_expression)
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("ALTER ROLE helix_app RESET helix.enforce")
    op.execute("ALTER ROLE helix_worker RESET helix.enforce")
