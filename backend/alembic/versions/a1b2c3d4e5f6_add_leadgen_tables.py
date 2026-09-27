"""Add leadgen tables (LeadGenJob, LeadGenLead, LeadGenWorkerHeartbeat).

Revision ID: a1b2c3d4e5f6
Revises: 51fc8263b0bc
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "51fc8263b0bc"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "leadgen_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(), server_default="queued"),
        sa.Column("stage", sa.String(), server_default="brief"),
        sa.Column("stage_label", sa.String(), nullable=True),
        sa.Column("stage_index", sa.Integer(), server_default="0"),
        sa.Column("stages_total", sa.Integer(), server_default="9"),
        sa.Column("brief", sa.JSON(), nullable=True),
        sa.Column("seeds", sa.JSON(), nullable=True),
        sa.Column("engine_default", sa.String(), server_default="stealth"),
        sa.Column("mode", sa.String(), server_default="crawl"),
        sa.Column("recipe_id", sa.String(), nullable=True),
        sa.Column("robots_obey", sa.Boolean(), server_default=sa.true()),
        sa.Column("adaptive", sa.Boolean(), server_default=sa.true()),
        sa.Column("capture_xhr_pattern", sa.String(), nullable=True),
        sa.Column("enrich_emails", sa.Boolean(), server_default=sa.true()),
        sa.Column("generate_outreach", sa.Boolean(), server_default=sa.true()),
        sa.Column("proxy_mode", sa.String(), server_default="off"),
        sa.Column("checkpoint_path", sa.String(), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=True),
        sa.Column("leads_count", sa.Integer(), server_default="0"),
        sa.Column("pages_fetched", sa.Integer(), server_default="0"),
        sa.Column("pages_blocked", sa.Integer(), server_default="0"),
        sa.Column("elapsed_ms", sa.Integer(), server_default="0"),
        sa.Column("credits_used", sa.Float(), server_default="0"),
        sa.Column("credit_budget", sa.Float(), server_default="0"),
        sa.Column("error_msg", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_boot_id", sa.String(), nullable=True),
    )
    op.create_table(
        "leadgen_leads",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("leadgen_jobs.id"), nullable=False),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("emails", sa.JSON(), nullable=True),
        sa.Column("phones", sa.JSON(), nullable=True),
        sa.Column("socials", sa.JSON(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("decision_makers", sa.JSON(), nullable=True),
        sa.Column("markdown_excerpt", sa.Text(), nullable=True),
        sa.Column("markdown_artifact_path", sa.String(), nullable=True),
        sa.Column("extract_status", sa.String(), server_default="empty"),
        sa.Column("fetch_status", sa.String(), server_default="ok"),
        sa.Column("engine_used", sa.String(), server_default="stealth"),
        sa.Column("email_source", sa.String(), server_default="none"),
        sa.Column("phone_source", sa.String(), server_default="none"),
        sa.Column("lead_score", sa.Integer(), server_default="0"),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("outreach", sa.JSON(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "leadgen_worker_heartbeat",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scrapling_version", sa.String(), nullable=True),
        sa.Column("engines", sa.JSON(), nullable=True),
        sa.Column("browsers_ready", sa.Boolean(), server_default=sa.false()),
        sa.Column("proxy_mode", sa.String(), server_default="off"),
        sa.Column("boot_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("leadgen_worker_heartbeat")
    op.drop_table("leadgen_leads")
    op.drop_table("leadgen_jobs")
