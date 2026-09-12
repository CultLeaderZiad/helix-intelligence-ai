from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    query = Column(String, nullable=False)
    status = Column(String, default="queued") # 'queued' | 'running' | 'succeeded' | 'failed'
    created_at = Column(DateTime(timezone=True), nullable=False)
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
