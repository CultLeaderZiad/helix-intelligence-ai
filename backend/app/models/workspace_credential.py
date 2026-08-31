from sqlalchemy import Column, String, DateTime, ForeignKey
from app.db.base import Base
import uuid
from datetime import datetime, timezone

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class WorkspaceProviderCredential(Base):
    __tablename__ = "workspace_provider_credentials"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String, nullable=False, default="google_gemini")
    encrypted_secret = Column(String, nullable=False)
    key_suffix = Column(String, nullable=True) # e.g. "abcd" for masked display
    status = Column(String, default="connected") # 'connected' | 'error' | 'untested'
    credential_mode = Column(String, default="managed") # 'managed' | 'byok'
    model = Column(String, nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
