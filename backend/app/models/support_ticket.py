from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, func
from app.db.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    type = Column(String, nullable=False, default="feedback") # 'feedback' | 'bug' | 'other'
    subject = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open") # 'open' | 'in_progress' | 'resolved'
    tag = Column(String, nullable=True) # e.g. 'discover', 'billing', 'create', 'intelligence'
    context_data = Column(JSON, default=dict, nullable=True) # page, plan, browser info
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SupportTicketReply(Base):
    __tablename__ = "support_ticket_replies"

    id = Column(String, primary_key=True, default=generate_uuid)
    ticket_id = Column(String, ForeignKey("support_tickets.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
