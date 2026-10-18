"""Exact idempotency keys, quota reservations, and a decimal credit ledger.

Amounts are Numeric, not binary floats. A reservation is the hold that a
charge or a media job settles or refunds exactly once.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func

from app.db.base import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class OperationIdempotency(Base):
    __tablename__ = "operation_idempotency"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "operation",
            "idempotency_key",
            name="uq_operation_idempotency_org_op_key",
        ),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    operation = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    job_id = Column(String, nullable=True)
    usage_log_id = Column(String, nullable=True)
    reservation_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CreditReservation(Base):
    __tablename__ = "credit_reservations"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    operation = Column(String, nullable=False)
    # Credits or quota units. Numeric so concurrent retries cannot drift.
    amount = Column(Numeric(20, 6), nullable=False)
    media_type = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | settled | refunded
    job_id = Column(String, nullable=True, index=True)
    idempotency_key = Column(String, nullable=True)
    payload_hash = Column(String, nullable=True)
    usage_log_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    settled_at = Column(DateTime(timezone=True), nullable=True)


class CreditLedgerEntry(Base):
    __tablename__ = "credit_ledger"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    usage_log_id = Column(String, ForeignKey("usage_logs.id"), nullable=True, index=True)
    reservation_id = Column(String, nullable=True, index=True)
    entry_kind = Column(String, nullable=False)  # debit | refund
    amount = Column(Numeric(20, 6), nullable=False)
    operation = Column(String, nullable=False)
    job_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
