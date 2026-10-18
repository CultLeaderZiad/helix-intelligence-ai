from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, ForeignKey, UniqueConstraint, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class UsageLog(Base):
    __tablename__ = "usage_logs"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "operation",
            "idempotency_key",
            name="uq_usage_logs_org_operation_idempotency_key",
        ),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    job_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False, index=True) # 'groq' | 'brightdata' | 'scrapegraph' | 'apify' | 'gemini' | 'openrouter'
    operation = Column(String, nullable=False, default="discover_search", server_default="discover_search") # 'discover_search' | 'landing_enrich' | 'pattern_synthesis' | 'chat'
    units = Column(Float, default=1.0) # tokens, requests, or records
    cost_usd = Column(Float, default=0.0) # real provider cost in USD
    credits_deducted = Column(Float, default=0.0) # credits deducted
    tokens_used = Column(Integer, default=0) # legacy/convenience token count
    requests_used = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict, nullable=True)
    idempotency_key = Column(String, nullable=True)
    payload_hash = Column(String, nullable=True)
    reservation_id = Column(String, nullable=True)
    ledger_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# Register ledger tables on Base.metadata for Alembic.
from app.models.credit_ledger import (
    CreditLedgerEntry as _CreditLedgerEntry,
    CreditReservation as _CreditReservation,
    OperationIdempotency as _OperationIdempotency,
)

_REGISTERED_LEDGER_TABLES = (_CreditLedgerEntry, _CreditReservation, _OperationIdempotency)

