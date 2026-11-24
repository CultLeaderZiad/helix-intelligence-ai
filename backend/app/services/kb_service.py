"""Admin knowledge base: upload, version, enable/disable, delete, search.

Documents are split into chunks on headings and blank lines, so the agent can
cite exactly which part it used (chunk id + document title/version). Uploading
a title that exists creates the next version and disables the older ones.
Search is Postgres full-text (simple + arabic configs), enabled docs only.
Retrieved text is admin-trusted content but is still handed to models as data,
never as instructions (see agent_service).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge_base import KbAudit, KbChunk, KbDocument

CHUNK_TARGET = 1200
CHUNK_MAX = 2000
ALLOWED_SUFFIXES = (".md", ".txt")


def chunk_text(body: str) -> List[str]:
    """Split on markdown headings and blank lines, packing paragraphs up to ~CHUNK_TARGET chars."""
    body = body.replace("\r\n", "\n").strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n|\n(?=#{1,6} )", body) if b.strip()]
    chunks: List[str] = []
    current = ""
    for block in blocks:
        while len(block) > CHUNK_MAX:  # a very long paragraph is cut at a sentence end when possible
            cut = max(block.rfind(". ", 0, CHUNK_MAX), block.rfind("\n", 0, CHUNK_MAX))
            cut = cut + 1 if cut > CHUNK_TARGET // 2 else CHUNK_MAX
            chunks.append(block[:cut].strip())
            block = block[cut:].strip()
        starts_section = block.startswith("#")
        if current and (starts_section or len(current) + len(block) + 2 > CHUNK_TARGET):
            chunks.append(current)
            current = block
        else:
            current = f"{current}\n\n{block}" if current else block
    if current:
        chunks.append(current)
    return chunks


def _view(doc: KbDocument, chunk_count: Optional[int] = None) -> Dict[str, Any]:
    return {
        "id": doc.id, "title": doc.title, "version": doc.version, "status": doc.status, "filename": doc.filename,
        "size_bytes": doc.size_bytes, "checksum": doc.checksum, "uploaded_by": doc.uploaded_by,
        "created_at": doc.created_at.isoformat() if doc.created_at else None, "chunks": chunk_count,
    }


async def upload(db: AsyncSession, actor_id: str, title: str, body: str, filename: Optional[str] = None) -> Dict[str, Any]:
    title = " ".join((title or "").split())[:200]
    if not title:
        raise HTTPException(status_code=422, detail={"code": "kb_title_required", "message": "A title is required."})
    if filename and not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(status_code=422, detail={"code": "kb_file_type", "message": "Upload a .md or .txt file."})
    raw = (body or "").encode("utf-8")
    if not raw.strip():
        raise HTTPException(status_code=422, detail={"code": "kb_empty", "message": "The document is empty."})
    if len(raw) > settings.KB_MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail={"code": "kb_file_too_large", "message": f"Max {settings.KB_MAX_FILE_BYTES} bytes per file."})
    total = int(await db.scalar(select(func.coalesce(func.sum(KbDocument.size_bytes), 0))) or 0)
    if total + len(raw) > settings.KB_MAX_TOTAL_BYTES:
        raise HTTPException(status_code=413, detail={"code": "kb_total_too_large", "message": "The knowledge base is full. Delete old versions first."})
    checksum = hashlib.sha256(raw).hexdigest()
    latest = (await db.execute(
        select(KbDocument).where(KbDocument.title == title).order_by(KbDocument.version.desc()).limit(1)
    )).scalar_one_or_none()
    if latest is not None and latest.checksum == checksum:
        raise HTTPException(status_code=409, detail={"code": "kb_unchanged", "message": "This exact version is already uploaded."})
    version = (latest.version + 1) if latest else 1
    await db.execute(update(KbDocument).where(KbDocument.title == title).values(status="disabled"))
    doc = KbDocument(title=title, version=version, status="enabled", filename=(filename or None),
                     size_bytes=len(raw), checksum=checksum, uploaded_by=actor_id)
    db.add(doc)
    await db.flush()
    parts = chunk_text(body)
    for i, part in enumerate(parts):
        db.add(KbChunk(document_id=doc.id, ordinal=i, text=part))
    db.add(KbAudit(actor_id=actor_id, action="upload", document_id=doc.id, title=title, version=version))
    await db.commit()
    await db.refresh(doc)
    return _view(doc, len(parts))


async def list_documents(db: AsyncSession) -> List[Dict[str, Any]]:
    counts = dict((await db.execute(select(KbChunk.document_id, func.count(KbChunk.id)).group_by(KbChunk.document_id))).all())
    docs = (await db.execute(select(KbDocument).order_by(KbDocument.title, KbDocument.version.desc()))).scalars().all()
    return [_view(d, counts.get(d.id, 0)) for d in docs]


async def _doc(db: AsyncSession, document_id: str) -> KbDocument:
    doc = await db.get(KbDocument, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def preview(db: AsyncSession, document_id: str) -> Dict[str, Any]:
    doc = await _doc(db, document_id)
    chunks = (await db.execute(select(KbChunk).where(KbChunk.document_id == doc.id).order_by(KbChunk.ordinal))).scalars().all()
    return {**_view(doc, len(chunks)), "chunk_items": [{"id": c.id, "ordinal": c.ordinal, "text": c.text} for c in chunks]}


async def set_status(db: AsyncSession, actor_id: str, document_id: str, enabled: bool) -> Dict[str, Any]:
    doc = await _doc(db, document_id)
    doc.status = "enabled" if enabled else "disabled"
    db.add(KbAudit(actor_id=actor_id, action="enable" if enabled else "disable", document_id=doc.id, title=doc.title, version=doc.version))
    await db.commit()
    return _view(doc)


async def delete(db: AsyncSession, actor_id: str, document_id: str) -> None:
    doc = await _doc(db, document_id)
    db.add(KbAudit(actor_id=actor_id, action="delete", document_id=doc.id, title=doc.title, version=doc.version))
    await db.delete(doc)
    await db.commit()


async def audit(db: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
    rows = (await db.execute(select(KbAudit).order_by(KbAudit.created_at.desc()).limit(min(limit, 500)))).scalars().all()
    return [{"id": r.id, "actor_id": r.actor_id, "action": r.action, "document_id": r.document_id, "title": r.title,
             "version": r.version, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


async def search(db: AsyncSession, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Top-k chunks of enabled documents for ``query``, with source ids for citing."""
    from app.services.text_search import clean_query, expand_query

    q = expand_query(clean_query(query))
    if not q:
        return []
    configs = ("simple", "arabic")
    match = " OR ".join(f"to_tsvector('{d}'::regconfig, c.text) @@ websearch_to_tsquery('{qc}'::regconfig, :q)"
                        for d in configs for qc in configs)
    score = " + ".join(f"ts_rank(to_tsvector('{d}'::regconfig, c.text), websearch_to_tsquery('{qc}'::regconfig, :q))"
                       for d in configs for qc in configs)
    rows = (await db.execute(text(
        f"SELECT c.id, c.document_id, c.ordinal, c.text, d.title, d.version, ({score}) AS score "
        f"FROM kb_chunks c JOIN kb_documents d ON d.id = c.document_id "
        f"WHERE d.status = 'enabled' AND ({match}) ORDER BY score DESC LIMIT :k"
    ), {"q": q, "k": max(1, min(int(k), 10))})).mappings().all()
    return [{"chunk_id": r["id"], "document_id": r["document_id"], "title": r["title"], "version": r["version"],
             "ordinal": r["ordinal"], "text": r["text"]} for r in rows]
