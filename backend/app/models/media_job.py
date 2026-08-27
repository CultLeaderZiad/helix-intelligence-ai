from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.db.base import Base
import uuid
from datetime import datetime, timezone

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class MediaGenerationJob(Base):
    __tablename__ = "media_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    status = Column(String, default="pending") # pending, processing, completed, failed
    prompt = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    provider_job_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    # Store dimensions, aspect ratio, model version, etc.
    parameters = Column(JSON, nullable=True) 
    
    # Results
    result_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
