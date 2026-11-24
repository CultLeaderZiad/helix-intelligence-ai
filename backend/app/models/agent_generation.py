"""Helix Agent output cached per workspace by input hash (ad variants, briefs).

Tenant table (RLS): the input includes the workspace's own product text.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, UniqueConstraint, func

from app.db.base import Base


class AgentGeneration(Base):
    __tablename__ = "agent_generations"
    __table_args__ = (UniqueConstraint("org_id", "kind", "input_hash", name="uq_agent_generations_org_kind_hash"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)  # 'variants' | 'brief'
    input_hash = Column(String(64), nullable=False)
    result = Column(JSON, nullable=False)
    model = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
