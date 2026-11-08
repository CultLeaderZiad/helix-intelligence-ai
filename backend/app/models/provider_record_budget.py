from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class ProviderRecordBudget(Base):
    """Records reserved per provider per calendar month (UTC). No tenant data."""

    __tablename__ = "provider_record_budget"

    provider = Column(String, primary_key=True)
    period_start = Column(Date, primary_key=True)
    records = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
