"""Patterns whose organization could not be verified.

Rows live here instead of `patterns` so list and compile paths have no
global-null branch to fall through.
"""

from sqlalchemy import Column, DateTime, Float, String, func

from app.db.base import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class PatternQuarantine(Base):
    __tablename__ = "pattern_quarantine"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, nullable=True)
    label = Column(String, nullable=False)
    family = Column(String, nullable=False)
    prevalence = Column(Float, nullable=False, default=0.0)
    lift_index = Column(Float, nullable=False, default=1.0)
    reason = Column(String, nullable=False)
    quarantined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
