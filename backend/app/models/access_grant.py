"""Manual access grants and the requests that lead to them.

A workspace can use a feature only while a platform admin grant is active.
Revoking or expiring a grant does not delete the workspace's data.
"""

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, func

from app.db.base import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    requested_features = Column(JSON, nullable=False)
    note = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(String, nullable=True)


class OrganizationAccessGrant(Base):
    __tablename__ = "organization_access_grants"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    plan_id = Column(String, nullable=False)
    feature_flags = Column(JSON, nullable=False)
    granted_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    request_id = Column(String, ForeignKey("access_requests.id"), nullable=True)
