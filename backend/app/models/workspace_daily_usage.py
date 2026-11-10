from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class WorkspaceDailyUsage(Base):
    """Per-workspace counters per UTC day, independent of credits.

    ``searches`` counts Discover searches started (cache hits excluded) and
    ``provider_calls`` counts paid provider calls. Refunds never lower them,
    so a refunded search still counts toward the workspace's daily caps.
    """

    __tablename__ = "workspace_daily_usage"

    day = Column(Date, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"), primary_key=True)
    searches = Column(Integer, nullable=False, server_default="0")
    provider_calls = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
