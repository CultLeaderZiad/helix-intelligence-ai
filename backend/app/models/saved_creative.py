from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class SavedCreative(Base):
    __tablename__ = "saved_creatives"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    creative_id = Column(String, ForeignKey("creatives.id"), nullable=False, index=True)
    collection_name = Column(String, default="Default", nullable=False, index=True)
    tags = Column(JSON, default=list, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
