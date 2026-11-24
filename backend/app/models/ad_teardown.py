"""AI teardown of one ad, cached by fingerprint and shared across workspaces.

Only public ad copy (headline, body, CTA, format, landing domain from the Meta
Ad Library) is analysed, never notes or annotations, so the same ad is
analysed once for everyone. Not a tenant table on purpose: it holds no
workspace data. Which workspace asked is recorded in usage_logs.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, String, func

from app.db.base import Base


class AdTeardown(Base):
    __tablename__ = "ad_teardowns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fingerprint = Column(String, nullable=False, unique=True)
    result = Column(JSON, nullable=False)
    model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
