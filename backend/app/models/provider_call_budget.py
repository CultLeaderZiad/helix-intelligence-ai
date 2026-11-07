from sqlalchemy import Column, Date, DateTime, Integer
from sqlalchemy.sql import func

from app.db.base import Base


class ProviderCallBudget(Base):
    """Global count of paid provider calls per UTC day (no tenant data)."""

    __tablename__ = "provider_call_budget"

    day = Column(Date, primary_key=True)
    calls = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
