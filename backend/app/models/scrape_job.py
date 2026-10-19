from datetime import datetime, timezone
import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, JSON, Index, func
from sqlalchemy.orm import relationship
from app.db.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    query = Column(String, nullable=False)
    # NULL means legacy/unknown request semantics: never reuse as cache.
    cache_identity = Column(String(64), nullable=True)
    status = Column(String, default="queued") # 'queued' | 'running' | 'succeeded' | 'failed'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    record_count = Column(Integer, default=0)
    
    # extra fields for frontend contract matching
    progress = Column(Float, default=0.0)
    stage = Column(String, nullable=True)
    stage_label = Column(String, nullable=True)
    stage_index = Column(Integer, default=0)
    stages_total = Column(Integer, default=1)
    elapsed_ms = Column(Integer, default=0)
    error_msg = Column(String, nullable=True)

    # Why the job failed, as a machine-readable value the UI can branch on:
    # 'service_restart' (the process died, nothing was wrong with the search)
    # or 'error' (the pipeline itself failed).
    failure_kind = Column(String, nullable=True)

    # Which process lifetime owns this job, and when that process last proved
    # it was still working on it. Together these let a restart identify dead
    # jobs by silence rather than by total age. See job_reconciliation.py.
    owner_boot_id = Column(String, nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)

    # Strategic Entity Intelligence & PR Dossier
    entity_profile = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_scrape_jobs_org_status_created", "org_id", "status", "created_at"),
        Index("uq_scrape_jobs_active_identity", "org_id", "cache_identity", unique=True,
              postgresql_where=sa.text("status IN ('queued', 'running') AND cache_identity IS NOT NULL")),
        Index("ix_scrape_jobs_cache_lookup", "org_id", "cache_identity", "status", "created_at"),
    )
