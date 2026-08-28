from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ExternalApiUsage(Base):
    __tablename__ = "external_api_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    provider = Column(String, nullable=False) # 'meta', 'apify', 'brightdata', 'scrapegraph', 'groq'
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Optional, depends if triggered by system
    query = Column(String, nullable=True) # Optional, context of the call
    max_records_requested = Column(Integer, nullable=True) # If applicable
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="attempted") # 'attempted', 'success', 'failed'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
