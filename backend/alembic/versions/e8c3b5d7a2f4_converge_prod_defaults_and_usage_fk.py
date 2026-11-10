"""Drop leftover prod defaults and require usage-log tenancy.

Revision ID: e8c3b5d7a2f4
Revises: d4f6a8c0e2b1
Create Date: 2026-10-18 23:30:00.000000

Production kept server defaults and a duplicate key_hash index that the
models do not declare. Fresh databases created by the earlier revisions
lack the organization foreign key and allow null usage-log owners.
This revision makes both shapes match the models.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8c3b5d7a2f4"
down_revision: Union[str, Sequence[str], None] = "d4f6a8c0e2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DROP_DEFAULTS = (
    ("api_keys", "id"),
    ("api_keys", "is_active"),
    ("plans", "type"),
    ("plans", "credit_allowance"),
    ("plans", "feature_flags"),
    ("usage_logs", "id"),
    ("users", "is_suspended"),
    ("users", "has_completed_onboarding"),
)


def _has_fk(table: str, name: str) -> bool:
    bind = op.get_bind()
    return name in {fk["name"] for fk in sa.inspect(bind).get_foreign_keys(table)}


def _has_unique(table: str, name: str) -> bool:
    bind = op.get_bind()
    return name in {item["name"] for item in sa.inspect(bind).get_unique_constraints(table)}


def upgrade() -> None:
    for table, column in _DROP_DEFAULTS:
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"))

    op.execute(
        sa.text(
            """
            UPDATE usage_logs AS u
            SET org_id = o.id
            FROM organizations AS o
            WHERE u.org_id IS NULL
              AND u.user_id IS NOT NULL
              AND o.owner_id = u.user_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE usage_logs AS u
            SET org_id = (
                SELECT id FROM organizations ORDER BY id LIMIT 1
            )
            WHERE u.org_id IS NULL
              AND EXISTS (SELECT 1 FROM organizations)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE usage_logs AS u
            SET user_id = o.owner_id
            FROM organizations AS o
            WHERE u.user_id IS NULL
              AND u.org_id = o.id
              AND o.owner_id IS NOT NULL
            """
        )
    )
    op.execute(sa.text("DELETE FROM usage_logs WHERE org_id IS NULL OR user_id IS NULL"))
    op.alter_column("usage_logs", "org_id", existing_type=sa.String(), nullable=False)
    op.alter_column("usage_logs", "user_id", existing_type=sa.String(), nullable=False)
    if not _has_fk("usage_logs", "usage_logs_org_id_fkey"):
        op.create_foreign_key(
            "usage_logs_org_id_fkey",
            "usage_logs",
            "organizations",
            ["org_id"],
            ["id"],
        )

    op.execute(sa.text("DROP INDEX IF EXISTS ix_api_keys_key_hash"))
    if not _has_unique("api_keys", "api_keys_key_hash_key"):
        op.create_unique_constraint("api_keys_key_hash_key", "api_keys", ["key_hash"])


def downgrade() -> None:
    if _has_unique("api_keys", "api_keys_key_hash_key"):
        op.drop_constraint("api_keys_key_hash_key", "api_keys", type_="unique")
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_api_keys_key_hash ON api_keys (key_hash)")
    )
    if _has_fk("usage_logs", "usage_logs_org_id_fkey"):
        op.drop_constraint("usage_logs_org_id_fkey", "usage_logs", type_="foreignkey")
    op.alter_column("usage_logs", "org_id", existing_type=sa.String(), nullable=True)
    op.alter_column("usage_logs", "user_id", existing_type=sa.String(), nullable=True)
    op.execute(sa.text("ALTER TABLE api_keys ALTER COLUMN id SET DEFAULT gen_random_uuid()::varchar"))
    op.execute(sa.text("ALTER TABLE api_keys ALTER COLUMN is_active SET DEFAULT true"))
    op.execute(sa.text("ALTER TABLE plans ALTER COLUMN type SET DEFAULT 'trial'"))
    op.execute(sa.text("ALTER TABLE plans ALTER COLUMN credit_allowance SET DEFAULT 25"))
    op.execute(sa.text("ALTER TABLE plans ALTER COLUMN feature_flags SET DEFAULT '{}'::jsonb"))
    op.execute(sa.text("ALTER TABLE usage_logs ALTER COLUMN id SET DEFAULT gen_random_uuid()::varchar"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN is_suspended SET DEFAULT false"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN has_completed_onboarding SET DEFAULT false"))
