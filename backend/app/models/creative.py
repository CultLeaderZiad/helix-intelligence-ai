from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Creative(Base):
    __tablename__ = "creatives"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("scrape_jobs.id"), nullable=False)
    
    brand_id = Column(String, nullable=False) # Maps to brand
    platform = Column(String, nullable=False) # 'meta'|'tiktok'|'youtube'|'linkedin'|'reddit'
    format = Column(String, nullable=False, default="video")
    
    headline = Column(String, nullable=True)
    body = Column(String, nullable=True)
    cta = Column(String, nullable=True)
    
    landing_domain = Column(String, nullable=True)
    thumbnail_ratio = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    first_seen = Column(String, nullable=True)
    last_seen = Column(String, nullable=True)
    days_active = Column(Integer, default=1)
    variant_count = Column(Integer, default=1)
    # the metrics can be linked or stored here (stored directly as columns for simplicity)
    impressions_est = Column(Integer, nullable=True)
    is_estimated = Column(Boolean, default=True, nullable=True)
    data_source = Column(String, default="meta_official", nullable=True) # 'meta_official'|'ad_library_scrape'|'organic_content_proxy'
    spend_band = Column(String, nullable=True) # 'low'|'mid'|'high'|'very_high'
    engagement_rate = Column(Float, nullable=True)
    ctr_est = Column(Float, nullable=True)
