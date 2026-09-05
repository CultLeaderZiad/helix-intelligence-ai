from sqlalchemy import Column, String, DateTime, func, Boolean, JSON
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    role = Column(String, default="customer") # 'customer' | 'assistant-admin' | 'admin'
    admin_permissions = Column(JSON, default=dict, nullable=True)
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_suspended = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    has_completed_onboarding = Column(Boolean, default=False)
    password_reset_token_hash = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
