"""Whop billing: one row per provider membership.

Additive only: a new tenant table with the same RLS policy and role grants as
every other org-scoped table. Downgrade drops it; access grants it created
stay (they are ordinary organization_access_grants rows).

Revision ID: c6e8a0b2d4f7
Revises: b5d7f9a1c3e6
"""
import sqlalchemy as sa
from alembic import op

revision = "c6e8a0b2d4f7"
down_revision = "b5d7f9a1c3e6"
branch_labels = None
depends_on = None

TABLE = "billing_subscriptions"
EXPR = (
    "(current_setting('helix.platform_admin', true) = '1' OR ("
    f"{TABLE}.org_id = ANY "
    "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))))"
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_membership_id", sa.String(), nullable=False),
        sa.Column("provider_plan_id", sa.String(), nullable=True),
        sa.Column("plan_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grant_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["grant_id"], ["organization_access_grants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_membership_id", name="uq_billing_subscriptions_provider_membership"),
    )
    op.create_index(op.f("ix_billing_subscriptions_org_id"), TABLE, ["org_id"], unique=False)
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {TABLE}_tenant_isolation ON {TABLE} FOR ALL USING {EXPR} WITH CHECK {EXPR}")
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO helix_app; END IF; "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN "
        f"GRANT SELECT ON {TABLE} TO helix_worker; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}")
    op.drop_index(op.f("ix_billing_subscriptions_org_id"), table_name=TABLE)
    op.drop_table(TABLE)
