"""W9-2: tags and notes on saved ads.

Additive only: two new tables with the same tenant RLS policy and role grants
as every other org-scoped table. Tags and notes cascade away with the saved ad.

Revision ID: a4c6e8f0b2d5
Revises: f2b4c6d8e0a1
"""

import sqlalchemy as sa
from alembic import op

revision = "a4c6e8f0b2d5"
down_revision = "f2b4c6d8e0a1"
branch_labels = None
depends_on = None

TABLES = ("saved_ad_tags", "saved_ad_notes")


def _expression(table: str) -> str:
    return (
        "(current_setting('helix.platform_admin', true) = '1' OR ("
        f"{table}.org_id = ANY "
        "(string_to_array(coalesce(current_setting('helix.org_ids', true), ''), ','))))"
    )


def upgrade() -> None:
    op.create_table(
        "saved_ad_tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("saved_creative_id", sa.String(), nullable=False),
        sa.Column("tag", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["saved_creative_id"], ["saved_creatives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("saved_creative_id", "tag", name="uq_saved_ad_tags_saved_tag"),
    )
    op.create_index(op.f("ix_saved_ad_tags_org_id"), "saved_ad_tags", ["org_id"], unique=False)
    op.create_index(op.f("ix_saved_ad_tags_saved_creative_id"), "saved_ad_tags", ["saved_creative_id"], unique=False)
    op.create_index(op.f("ix_saved_ad_tags_tag"), "saved_ad_tags", ["tag"], unique=False)

    op.create_table(
        "saved_ad_notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("saved_creative_id", sa.String(), nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["saved_creative_id"], ["saved_creatives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_ad_notes_org_id"), "saved_ad_notes", ["org_id"], unique=False)
    op.create_index(op.f("ix_saved_ad_notes_saved_creative_id"), "saved_ad_notes", ["saved_creative_id"], unique=False)

    for table in TABLES:
        expr = _expression(table)
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} FOR ALL USING {expr} WITH CHECK {expr}")
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO helix_app; END IF; "
            "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_worker') THEN "
            f"GRANT SELECT ON {table} TO helix_worker; END IF; "
            "END $$"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_index(op.f("ix_saved_ad_notes_saved_creative_id"), table_name="saved_ad_notes")
    op.drop_index(op.f("ix_saved_ad_notes_org_id"), table_name="saved_ad_notes")
    op.drop_table("saved_ad_notes")
    op.drop_index(op.f("ix_saved_ad_tags_tag"), table_name="saved_ad_tags")
    op.drop_index(op.f("ix_saved_ad_tags_saved_creative_id"), table_name="saved_ad_tags")
    op.drop_index(op.f("ix_saved_ad_tags_org_id"), table_name="saved_ad_tags")
    op.drop_table("saved_ad_tags")
