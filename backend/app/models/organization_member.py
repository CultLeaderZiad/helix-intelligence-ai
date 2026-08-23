from sqlalchemy import Column, String, DateTime, ForeignKey, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="member", nullable=False) # 'owner' | 'admin' | 'member'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrganizationInvite(Base):
    __tablename__ = "organization_invites"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(String, default="member", nullable=False)
    invited_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False) # 'pending' | 'accepted' | 'canceled'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
