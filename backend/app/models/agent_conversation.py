"""Ask Helix conversations and their messages (saved history).

Tenant tables with RLS by workspace AND by user: a conversation is private to the user who
had it. Nothing is deleted automatically; past the per-user cap the oldest unpinned
conversation is archived, still readable and restorable.
"""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, String, Text, func

from app.db.base import Base


def _uuid():
    return str(uuid.uuid4())


class AgentConversation(Base):
    __tablename__ = "agent_conversations"
    __table_args__ = (Index("ix_agent_conversations_user_updated", "org_id", "user_id", "updated_at"),)

    id = Column(String, primary_key=True, default=_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    pinned = Column(Boolean, nullable=False, server_default="false", default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (Index("ix_agent_messages_conversation_created", "conversation_id", "created_at"),)

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    # Assistant turns only: citations, proposals, references, tools_used, model, effort, label.
    payload = Column(JSON, nullable=False, server_default="{}", default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
