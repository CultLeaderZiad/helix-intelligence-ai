from sqlalchemy import Column, String, ForeignKey, Float, JSON, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan_id = Column(String, default="plan_trial_default", nullable=False)
    plan = Column(String, default="trial") # Legacy text field fallback ('trial' | 'pay_as_you_go' | 'custom')
    credit_balance = Column(Float, default=25.0, nullable=False)
    credits_used = Column(Float, default=0.0, nullable=False)
    daily_credits_used_today = Column(Float, default=0.0, nullable=False)
    daily_credits_reset_at = Column(DateTime(timezone=True), nullable=True) # last UTC midnight when daily counter was reset
    custom_feature_flags = Column(JSON, default=dict, nullable=True)
    status = Column(String, default="active", nullable=False) # 'active' | 'trial_expired' | 'quota_exhausted' | 'suspended' | 'daily_limit_reached'

