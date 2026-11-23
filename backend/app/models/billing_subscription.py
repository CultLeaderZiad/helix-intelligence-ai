"""A workspace's subscription at an external billing provider (Whop).

One row per provider membership. It remembers which workspace a membership
pays for, the last state applied (so late or out-of-order webhooks never undo
a newer one) and the access grant it created, so a cancellation only revokes
that grant, never one an admin gave. Tenant RLS scopes it like every org table.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_membership_id", name="uq_billing_subscriptions_provider_membership"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    provider_membership_id = Column(String, nullable=False)
    provider_plan_id = Column(String, nullable=True)
    plan_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    grant_id = Column(String, ForeignKey("organization_access_grants.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
