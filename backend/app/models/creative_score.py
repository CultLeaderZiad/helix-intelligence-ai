from sqlalchemy import Column, String, Float, ForeignKey
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class CreativeScore(Base):
    __tablename__ = "creative_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    creative_id = Column(String, ForeignKey("creatives.id"), nullable=False, unique=True)
    
    hook = Column(Float, nullable=True)
    clarity = Column(Float, nullable=True) # Renamed to clarity to match contracts.js (retention -> clarity -> composite)
    retention = Column(Float, nullable=True)
    composite = Column(Float, nullable=True)
