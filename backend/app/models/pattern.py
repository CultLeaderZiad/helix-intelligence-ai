from sqlalchemy import Column, String, Float, ForeignKey
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(String, primary_key=True, default=generate_uuid)
    # the request mentions job_id but the contract uses pattern globally with a family/label, 
    # we'll include job_id to tie it to a run if needed
    job_id = Column(String, ForeignKey("scrape_jobs.id"), nullable=True)
    
    label = Column(String, nullable=False)
    family = Column(String, nullable=False)
    prevalence = Column(Float, nullable=False, default=0.0)
    lift_index = Column(Float, nullable=False, default=1.0)
