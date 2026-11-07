"""Saved Discover search drafts.

A draft is a search a user wants to run or re-run later (query, notes and the
filters they had set). It is stored per user inside one workspace so it
follows the user across browsers and devices instead of living only in
localStorage.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class SearchDraft(Base):
    __tablename__ = "search_drafts"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    query = Column(String(500), nullable=False)
    notes = Column(String(2000), nullable=False, server_default="", default="")
    filters = Column(JSON, nullable=False, server_default="{}", default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
