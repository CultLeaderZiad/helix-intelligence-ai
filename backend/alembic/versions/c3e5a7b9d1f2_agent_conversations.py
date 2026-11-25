"""Ask Helix saved conversations (history).

Additive only: two new tables with RLS by workspace and by user. Nothing existing is dropped.
NOT applied to production by the author: apply with a Neon backup and the owner's approval.

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
"""

import sqlalchemy as sa
from alembic import op

revision = "c3e5a7b9d1f2"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None

_TABLES = ("agent_conversations", "agent_messages")


def _expression(table: str) -> str:
    return (
        "(current_setting('helix.platform_admin', true) = '1' OR ("
        f"{table}.org_id = ANY (string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ',')) "
        f"AND {table}.user_id = coalesce(current_setting('helix.user_id', true), '')))"
    )


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_conversations_org_id"), "agent_conversations", ["org_id"])
    op.create_index(op.f("ix_agent_conversations_user_id"), "agent_conversations", ["user_id"])
    op.create_index("ix_agent_conversations_user_updated", "agent_conversations", ["org_id", "user_id", "updated_at"])

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_messages_conversation_id"), "agent_messages", ["conversation_id"])
    op.create_index(op.f("ix_agent_messages_org_id"), "agent_messages", ["org_id"])
    op.create_index(op.f("ix_agent_messages_user_id"), "agent_messages", ["user_id"])
    op.create_index("ix_agent_messages_conversation_created", "agent_messages", ["conversation_id", "created_at"])

    for table in _TABLES:
        expr = _expression(table)
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} FOR ALL USING {expr} WITH CHECK {expr}")
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO helix_app; END IF; "
            "END $$"
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("agent_messages")
    op.drop_table("agent_conversations")
