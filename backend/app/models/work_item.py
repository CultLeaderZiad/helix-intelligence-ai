"""Durable claim row for long AI and scraping work."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "kind",
            "idempotency_key",
            name="uq_work_items_org_kind_key",
        ),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True)
    kind = Column(String, nullable=False)
    job_id = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="queued")
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    max_attempts = Column(Integer, nullable=False, default=3, server_default="3")
    lease_owner = Column(String, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    provider_operation_id = Column(String, nullable=True)
    provider_started_at = Column(DateTime(timezone=True), nullable=True)
    cancel_requested = Column(String, nullable=True)
    last_error = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=False)
    available_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
