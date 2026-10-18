"""Manual access grants and explicit scout/leadgen/monitors flags.

Revision ID: f8b3c4d5e6a7
Revises: e7c1a9b4d2f0
Create Date: 2026-10-18 21:20:00.000000

Does not invent prices or a billing provider. Seeded plan rows gain
scout, leadgen, and monitors keys set to false until a platform admin
grant turns a feature on for one organization.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8b3c4d5e6a7"
down_revision: Union[str, Sequence[str], None] = "e7c1a9b4d2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_platform_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute("UPDATE users SET is_platform_admin = true WHERE role = 'admin'")

    op.create_table(
        "access_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("requested_features", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_by_user_id", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_requests_org_id", "access_requests", ["org_id"])
    op.create_index("ix_access_requests_user_id", "access_requests", ["user_id"])

    op.create_table(
        "organization_access_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("feature_flags", sa.JSON(), nullable=False),
        sa.Column("granted_by_user_id", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["access_requests.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organization_access_grants_org_id", "organization_access_grants", ["org_id"])

    op.execute(
        """
        UPDATE plans
        SET feature_flags = (
            COALESCE(feature_flags::jsonb, '{}'::jsonb)
            || '{"scout": false, "leadgen": false, "monitors": false}'::jsonb
        )::json
        """
    )

    for table in ("access_requests", "organization_access_grants"):
        predicate = (
            "org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))"
        )
        expression = f"""(
            current_setting('helix.enforce', true) IS DISTINCT FROM '1'
            OR current_setting('helix.platform_admin', true) = '1'
            OR {predicate}
        )"""
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"FOR ALL USING {expression} WITH CHECK {expression}"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON access_requests TO helix_app, helix_worker")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON organization_access_grants TO helix_app, helix_worker"
    )


def downgrade() -> None:
    for table in ("organization_access_grants", "access_requests"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_organization_access_grants_org_id", table_name="organization_access_grants")
    op.drop_table("organization_access_grants")
    op.drop_index("ix_access_requests_user_id", table_name="access_requests")
    op.drop_index("ix_access_requests_org_id", table_name="access_requests")
    op.drop_table("access_requests")
    op.drop_column("users", "is_platform_admin")
    op.execute(
        """
        UPDATE plans
        SET feature_flags = (COALESCE(feature_flags::jsonb, '{}'::jsonb) - 'scout' - 'leadgen' - 'monitors')::json
        """
    )
