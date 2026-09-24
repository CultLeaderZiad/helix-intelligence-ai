"""Lead Generation models — NEW tables, deliberately separate from ScoutJob /
ScoutLead so the existing Social/Atlas path is never touched.

DECISION (locked): LeadGenJob + LeadGenLead. No job_kind on ScoutJob.

LeadGenWorkerHeartbeat is a tiny worker-registry row so GET /worker/health can
report truthful online/offline + engine details without guessing from job state.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class LeadGenJob(Base):
    __tablename__ = "leadgen_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Canonical: queued | running | paused | succeeded | failed
    status = Column(String, default="queued")
    stage = Column(String, default="brief")           # brief|seed|discover|fetch|extract|enrich|score|outreach|export
    stage_label = Column(String, default="Job queued")
    stage_index = Column(Integer, default=0)
    stages_total = Column(Integer, default=9)

    brief = Column(JSON, default=dict)                # validated ICP brief
    seeds = Column(JSON, default=list)                # normalized absolute https URLs

    engine_default = Column(String, default="stealth")  # http | stealth | dynamic
    mode = Column(String, default="crawl")              # crawl|sitemap|shopify|csv_feed|digest
    recipe_id = Column(String, nullable=True)
    robots_obey = Column(Boolean, default=True)         # default ON; disable requires explicit flag + audit log
    adaptive = Column(Boolean, default=True)
    capture_xhr_pattern = Column(String, nullable=True)
    enrich_emails = Column(Boolean, default=True)
    generate_outreach = Column(Boolean, default=True)
    proxy_mode = Column(String, default="off")          # off | org | job
    checkpoint_path = Column(String, nullable=True)

    logs = Column(JSON, default=list)                 # canonical "> stage · detail" lines

    leads_count = Column(Integer, default=0)
    pages_fetched = Column(Integer, default=0)
    pages_blocked = Column(Integer, default=0)
    elapsed_ms = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    credit_budget = Column(Float, default=0.0)
    error_msg = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    owner_boot_id = Column(String, nullable=True)

    leads = relationship("LeadGenLead", back_populates="job", cascade="all, delete-orphan")


class LeadGenLead(Base):
    __tablename__ = "leadgen_leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("leadgen_jobs.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)

    company_name = Column(String, nullable=True)
    website = Column(String, nullable=True)
    domain = Column(String, nullable=True)

    emails = Column(JSON, default=list)               # provenance in sources + email_source
    phones = Column(JSON, default=list)
    socials = Column(JSON, default=dict)
    address = Column(String, nullable=True)
    decision_makers = Column(JSON, default=list)

    markdown_excerpt = Column(Text, nullable=True)
    markdown_artifact_path = Column(String, nullable=True)

    extract_status = Column(String, default="empty")   # empty | partial | ok | failed
    fetch_status = Column(String, default="ok")        # ok | blocked | rate_limited | error
    engine_used = Column(String, default="stealth")    # http | stealth | dynamic

    email_source = Column(String, default="none")      # website | hunter | bio | none
    phone_source = Column(String, default="none")      # website | bio | none

    lead_score = Column(Integer, default=0)            # 0..100
    priority = Column(String, nullable=True)           # high | med | low
    outreach = Column(JSON, nullable=True)             # {subject, body, dm, personalization_points} | null
    sources = Column(JSON, default=dict)               # raw provenance, selector hits, urls visited, score breakdown

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("LeadGenJob", back_populates="leads")


class LeadGenWorkerHeartbeat(Base):
    """One row the Scrapling worker upserts every ~30s so /worker/health can
    truthfully report online/offline + engine details. Not a job or lead
    table — does not touch Social/Atlas models."""
    __tablename__ = "leadgen_worker_heartbeat"

    id = Column(String, primary_key=True, default="scrapling_worker")
    scrapling_version = Column(String, nullable=True)
    engines = Column(JSON, default=list)
    browsers_ready = Column(Boolean, default=False)
    proxy_mode = Column(String, default="off")
    boot_id = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
