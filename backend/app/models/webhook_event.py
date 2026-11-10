from sqlalchemy import Column, String, DateTime, JSON, UniqueConstraint
from app.db.base import Base
import uuid
from datetime import datetime, timezone

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_webhook_events_provider_event_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, index=True, nullable=False)
    event_id = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=False) # pending, processed, failed
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
