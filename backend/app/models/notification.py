from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    type = Column(String, nullable=False, default="info") # 'info' | 'alert' | 'system' | 'creative_found' | 'quota'
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
