"""W9-2: tags and notes on saved ads (a row of ``saved_creatives``).

Both tables carry ``org_id`` so tenant RLS scopes them to the workspace like
every other org table. Removing a saved ad removes its tags and notes
(``ON DELETE CASCADE``). The old ``saved_creatives.tags`` JSON column was never
written by the UI and is left alone.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class SavedAdTag(Base):
    __tablename__ = "saved_ad_tags"
    __table_args__ = (UniqueConstraint("saved_creative_id", "tag", name="uq_saved_ad_tags_saved_tag"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    saved_creative_id = Column(String, ForeignKey("saved_creatives.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(40), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SavedAdNote(Base):
    __tablename__ = "saved_ad_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    saved_creative_id = Column(String, ForeignKey("saved_creatives.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
