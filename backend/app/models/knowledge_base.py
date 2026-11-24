"""Admin knowledge base: documents, their search chunks, and an audit log."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func

from app.db.base import Base


def _id():
    return str(uuid.uuid4())


class KbDocument(Base):
    __tablename__ = "kb_documents"
    __table_args__ = (UniqueConstraint("title", "version", name="uq_kb_documents_title_version"),)

    id = Column(String, primary_key=True, default=_id)
    title = Column(String(200), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="enabled")  # 'enabled' | 'disabled'
    filename = Column(String(200), nullable=True)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (
        Index("ix_kb_chunks_document_id", "document_id"),
    )

    id = Column(String, primary_key=True, default=_id)
    document_id = Column(String, ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False)
    ordinal = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)


class KbAudit(Base):
    __tablename__ = "kb_audit"

    id = Column(String, primary_key=True, default=_id)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # 'upload' | 'enable' | 'disable' | 'delete'
    document_id = Column(String, nullable=True)
    title = Column(String(200), nullable=True)
    version = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
