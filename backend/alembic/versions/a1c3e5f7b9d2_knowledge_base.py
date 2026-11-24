"""Knowledge base: admin-uploaded documents split into searchable chunks.

Additive only. Platform-wide content written only by full admins, read by
the agent for every workspace, so no tenant RLS. Full-text search uses GIN
expression indexes on to_tsvector(simple|arabic, text), like the W9 indexes.

Revision ID: a1c3e5f7b9d2
Revises: f9b1d3e5a7c0
"""
import sqlalchemy as sa
from alembic import op

revision = "a1c3e5f7b9d2"
down_revision = "f9b1d3e5a7c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title", "version", name="uq_kb_documents_title_version"),
    )
    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["kb_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])
    for config in ("simple", "arabic"):
        op.execute(f"CREATE INDEX ix_kb_chunks_fts_{config} ON kb_chunks USING gin (to_tsvector('{config}'::regconfig, text))")
    op.create_table(
        "kb_audit",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helix_app') THEN "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON kb_documents, kb_chunks TO helix_app; "
        "GRANT SELECT, INSERT ON kb_audit TO helix_app; END IF; "
        "END $$"
    )


def downgrade() -> None:
    op.drop_table("kb_audit")
    for config in ("simple", "arabic"):
        op.execute(f"DROP INDEX IF EXISTS ix_kb_chunks_fts_{config}")
    op.drop_index("ix_kb_chunks_document_id", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_table("kb_documents")
