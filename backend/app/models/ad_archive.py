"""Permanent per-workspace copy of ads that Discover found.

Ad Library media URLs expire and ads get taken down; the archive keeps the
text and a re-hosted copy of the media so a saved finding stays readable.
``creative_id`` is a plain reference, not a foreign key, so an archive entry
outlives the creative row it was copied from.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class AdArchiveEntry(Base):
    __tablename__ = "ad_archive"
    __table_args__ = (UniqueConstraint("org_id", "archive_key", name="uq_ad_archive_org_key"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    # Ad Library id when known, otherwise a hash of platform + brand + text.
    archive_key = Column(String, nullable=False)
    creative_id = Column(String, nullable=True, index=True)
    job_id = Column(String, nullable=True)
    platform = Column(String, nullable=False)
    source_ad_id = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    format = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    body = Column(String, nullable=True)
    cta = Column(String, nullable=True)
    landing_domain = Column(String, nullable=True)
    permalink = Column(String, nullable=True)
    first_seen = Column(String, nullable=True)
    last_seen = Column(String, nullable=True)
    days_active = Column(Integer, nullable=True)
    original_media_url = Column(String, nullable=True)
    original_thumbnail_url = Column(String, nullable=True)
    media_ref = Column(String, nullable=True)
    thumbnail_ref = Column(String, nullable=True)
    # stored | too_large | not_allowed | failed | none
    media_status = Column(String, nullable=False, default="none", server_default="none")
    media_bytes = Column(Integer, nullable=False, default=0, server_default="0")
    archived_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
