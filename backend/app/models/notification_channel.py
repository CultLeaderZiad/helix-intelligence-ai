"""Outbound alert channels for a workspace: Telegram chats and signed webhooks.

``config_encrypted`` holds the secret part (Telegram chat id, webhook URL and
signing secret) as a Fernet token (security_service.encrypt_secret); ``label``
is the masked, display-only part. A Telegram channel starts ``pending`` with a
one-time link code (stored hashed) until the bot receives ``/start <code>``.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.base import Base


def generate_uuid():
    return str(uuid.uuid4())


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # 'telegram' | 'webhook'
    status = Column(String, nullable=False, default="active")  # 'pending' | 'active' | 'disabled'
    label = Column(String, nullable=False, default="")
    config_encrypted = Column(Text, nullable=True)
    link_code_hash = Column(String, nullable=True, unique=True)
    link_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
