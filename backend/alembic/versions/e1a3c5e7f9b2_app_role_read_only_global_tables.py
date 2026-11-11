"""App roles get read-only access to global tables they never write.

These tables are shared by every workspace and have no RLS. The API and
worker code never writes them, but helix_app (and helix_worker) held
INSERT/UPDATE/DELETE. A bug or injection in the app could have rewritten the
migration revision or webhook history. Only the owner (migrations) writes them
now. Tables the app does write (plans, app_updates, provider budgets) keep
their grants. Grants only; no data changes.

Revision ID: e1a3c5e7f9b2
Revises: d0e2f4a6b8c1
"""

from alembic import op

revision = "e1a3c5e7f9b2"
down_revision = "d0e2f4a6b8c1"
branch_labels = None
depends_on = None

TABLES = ("alembic_version", "webhook_events", "pattern_quarantine", "leadgen_worker_heartbeat")
ROLES = ("helix_app", "helix_worker", "helix_api_login", "helix_worker_login")


def _each(statement: str) -> None:
    for table in TABLES:
        for role in ROLES:
            op.execute(f"""
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}')
     AND to_regclass('public.{table}') IS NOT NULL THEN
    EXECUTE {statement!r};
  END IF;
END $$""".replace("{T}", table).replace("{R}", role))


def upgrade() -> None:
    _each("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.{T} FROM {R}")


def downgrade() -> None:
    # Restores what helix_app had; the login roles inherit it.
    for table in TABLES:
        op.execute(f"""
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app')
     AND to_regclass('public.{table}') IS NOT NULL THEN
    GRANT INSERT, UPDATE, DELETE ON public.{table} TO helix_app;
  END IF;
END $$""")
