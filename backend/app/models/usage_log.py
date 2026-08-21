from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    tokens_used = Column(Integer, default=0)
    requests_used = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
