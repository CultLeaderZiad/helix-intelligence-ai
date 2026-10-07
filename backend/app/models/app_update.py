import datetime
import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Boolean, DateTime, Text, func
from app.db.base import Base

class AppUpdate(Base):
    __tablename__ = "app_updates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    level = Column(String(50), default="info", server_default="info", nullable=False)  # info | warning | success | critical
    category = Column(String(100), default="General", server_default="General", nullable=True)  # Platform, AI Engine, API, Scraper, etc.
    is_published = Column(Boolean, default=False, server_default=sa.false(), nullable=False)
    show_as_banner = Column(Boolean, default=False, server_default=sa.false(), nullable=False)
    banner_dismissible = Column(Boolean, default=True, server_default=sa.true(), nullable=False)
    show_on_public = Column(Boolean, default=True, server_default=sa.true(), nullable=False)
    link_url = Column(String(500), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), server_default=func.now(), onupdate=func.now(), nullable=False)
