import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class ScoutJob(Base):
    __tablename__ = "scout_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="queued")  # queued | running | succeeded | failed
    platforms = Column(JSON, default=list)     # ["instagram", "github", "linktree", ...]
    handles = Column(JSON, default=list)       # ["helixagency", "cultleaderziad", ...]
    enrich_emails = Column(Boolean, default=True)
    target_category = Column(String, nullable=True) # e.g. "beauty clinics MENA"
    generate_outreach = Column(Boolean, default=True)

    stage = Column(String, default="queued")   # queued | init | scrape | enrich | complete | failed
    stage_label = Column(String, default="Job queued")
    stage_index = Column(Integer, default=0)
    stages_total = Column(Integer, default=4)
    logs = Column(JSON, default=list)          # ["> github:cultleaderziad · ok", ...]

    leads_count = Column(Integer, default=0)
    elapsed_ms = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    error_msg = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    owner_boot_id = Column(String, nullable=True)

    leads = relationship("ScoutLead", back_populates="job", cascade="all, delete-orphan")


class ScoutLead(Base):
    __tablename__ = "scout_leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("scout_jobs.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    platform = Column(String, nullable=False) # instagram | github | linktree | tiktok | youtube | twitch | pinterest | linkedin
    handle = Column(String, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    followers = Column(Integer, default=0)
    lead_score = Column(Integer, default=0)   # 0..100
    profile_url = Column(String, nullable=True)
    scrape_status = Column(String, default="ok") # ok | needs_manual_review | rate_limited | not_found
    atlas = Column(JSON, default=dict)        # full Atlas JSON contract
    sources = Column(JSON, default=dict)      # {"email_source": "bio", "confidence": 90, ...}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ScoutJob", back_populates="leads")


class ScoutMapsJob(Base):
    __tablename__ = "scout_maps_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="queued")  # queued | running | succeeded | failed
    keyword = Column(String, nullable=False)
    city = Column(String, nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    depth = Column(Integer, default=5)
    extract_emails = Column(Boolean, default=True)
    pull_socials = Column(Boolean, default=False)

    stage = Column(String, default="queued")   # queued | geocode | search | enrich | complete | failed
    stage_label = Column(String, default="Job queued")
    stage_index = Column(Integer, default=0)
    stages_total = Column(Integer, default=4)
    logs = Column(JSON, default=list)

    results_count = Column(Integer, default=0)
    elapsed_ms = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    error_msg = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    owner_boot_id = Column(String, nullable=True)

    leads = relationship("ScoutMapsLead", back_populates="job", cascade="all, delete-orphan")


class ScoutMapsLead(Base):
    __tablename__ = "scout_maps_leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("scout_maps_jobs.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    emails_found = Column(JSON, default=list)
    website = Column(String, nullable=True)
    category = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, default=0)
    instagram = Column(String, nullable=True)
    facebook = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    socials = Column(JSON, default=dict)
    metadata_raw = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ScoutMapsJob", back_populates="leads")
