from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, default="trial") # 'trial' | 'pay_as_you_go' | 'custom'
    credit_allowance = Column(Integer, default=25)
    price_per_credit = Column(Float, nullable=True) # in USD, e.g. 0.01
    feature_flags = Column(JSON, default=dict) # {"discover": true, "intelligence": true, "create": true, "performance": true, "swipe_files": true, "team_accounts": false, "public_api": false}
    created_by_admin_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
