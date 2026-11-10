"""Guest links for boards: signed, read-only, revocable, expiring.

A board is a user's ``saved_creatives`` collection inside one workspace. The
link row is the revocation and expiry record; the token in the URL is an HMAC
over the row's id, workspace and expiry, so a guessed id is useless and a
revoked or expired row closes the link even if the token is still valid.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class BoardShareLink(Base):
    __tablename__ = "board_share_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    collection_name = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
