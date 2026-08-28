import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.db.base import Base

class AppUpdate(Base):
    __tablename__ = "app_updates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    level = Column(String(50), default="info", nullable=False)  # info | warning | success | critical
    is_published = Column(Boolean, default=False, nullable=False)
    show_as_banner = Column(Boolean, default=False, nullable=False)
    banner_dismissible = Column(Boolean, default=True, nullable=False)
    show_on_public = Column(Boolean, default=True, nullable=False)
    link_url = Column(String(500), nullable=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
