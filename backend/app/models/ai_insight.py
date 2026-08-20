from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(String, primary_key=True, default=generate_uuid)
    creative_id = Column(String, ForeignKey("creatives.id"), nullable=False)
    
    kind = Column(String, nullable=False, default="opportunity") # 'hook_analysis'|'risk'|'opportunity'
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    reasons = Column(JSON, nullable=True) # Assuming 'reasons' maps to evidence or detailed explanation
    confidence = Column(Float, nullable=False, default=0.0)
    
    # extra fields for frontend contract matching
    evidence_creative_ids = Column(JSON, nullable=True) # list of ids
    generated_at = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
