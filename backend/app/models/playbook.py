from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from app.db.base import Base
import uuid
import secrets

def generate_uuid():
    return str(uuid.uuid4())

def generate_public_id():
    return f"pb_{secrets.token_urlsafe(12)}"

class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(String, primary_key=True, default=generate_uuid)
    public_id = Column(String, unique=True, index=True, default=generate_public_id, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    brand_name = Column(String, nullable=False, index=True)
    query = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    patterns = Column(JSON, default=list, nullable=False) # Top 3-5 extracted patterns with lift%
    creatives = Column(JSON, default=list, nullable=False) # Real scraped creatives with attribution
    insights = Column(JSON, default=list, nullable=False) # Key Deep Teardown takeaways
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
