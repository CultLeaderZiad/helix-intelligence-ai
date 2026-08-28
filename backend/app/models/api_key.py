from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, default="Default API Key")
    key_hash = Column(String, nullable=False, index=True)
    prefix = Column(String, nullable=False) # e.g. "hlx_live_a1b2..."
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
