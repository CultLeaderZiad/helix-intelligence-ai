"""Knowledge-base file import: .md, .txt, .csv, .pdf and .zip uploads, read fully on the server.

Each text file (and each text file inside a zip) becomes its own document, titled
from its front matter or its file name, so the agent can cite the exact article.
A YAML front matter block becomes a title line, a summary, tags and sources; slug,
level and updated are dropped. The article text itself is never rewritten.

Archives are read in memory, never written to disk, so a hostile path cannot
escape anywhere. Limits: KB_MAX_ZIP_BYTES for the upload, KB_MAX_ZIP_ENTRIES
entries, KB_MAX_FILE_BYTES per file (declared and actually read), and the whole
knowledge base stays under KB_MAX_TOTAL_BYTES. Encrypted entries, nested archives,
hidden files, README files and anything that is not .md, .txt, .csv or .pdf are skipped, and
every skip is reported with its reason.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import kb_service

TEXT_SUFFIXES = (".md", ".txt", ".csv", ".pdf")
MAX_PDF_PAGES = 100
MAX_FILES_PER_REQUEST = 20


def split_front_matter(body: str) -> Tuple[Dict[str, str], List[str], str]:
    """(fields, sources, rest). Text without a front matter block is returned as is."""
    body = body.replace("\r\n", "\n")
    if not body.startswith("---\n"):
        return {}, [], body
    end = body.find("\n---", 4)
    if end == -1:
        return {}, [], body
    head, rest = body[4:end], body[end + 4:].lstrip("\n")
    meta: Dict[str, str] = {}
    sources: List[str] = []
    key = ""
    for line in head.splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            meta[key] = match.group(2).strip().strip('"')
        elif key == "sources" and line.strip().startswith("- "):
            sources.append(line.strip()[2:].strip().strip('"'))
    return meta, sources, rest


def prepare_document(body: str) -> str:
    """Front matter -> title, summary, tags and sources; the article text is kept as written."""
    meta, sources, rest = split_front_matter(body)
    if not meta and not sources:
        return rest
    title = meta.get("title", "").strip()
    parts = [meta.get("summary", "").strip()]
    tags = meta.get("tags", "").strip("[]")
    if tags:
        parts.append("Tags: " + ", ".join(t.strip() for t in tags.split(",") if t.strip()))
    if sources:
        parts.append("Sources: " + "; ".join(sources))
    intro = "\n".join(p for p in parts if p)
    own_title = rest.lstrip().startswith("# ")
    if intro and own_title:
        first, _, remainder = rest.lstrip().partition("\n")
        return f"{first}\n\n{intro}\n\n{remainder.lstrip()}"
    heading = f"## {title}\n\n" if title else ""
    return f"{heading}{intro}\n\n{rest}" if intro else f"{heading}{rest}"


def document_title(body: str, filename: str) -> str:
    meta, _, _ = split_front_matter(body)
    title = meta.get("title", "").strip()
    if not title:
        stem = PurePosixPath(filename).stem
        title = re.sub(r"[-_]+", " ", stem).strip().capitalize()
    return " ".join(title.split())[:200] or "Untitled"


def _clean_name(raw: str) -> str:
    return PurePosixPath(str(raw or "").replace("\\", "/")).name


def _pdf_text(raw: bytes) -> Optional[str]:
    """Text of the first MAX_PDF_PAGES pages. None for a scanned, encrypted or broken PDF."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            return None
        pages = [(page.extract_text() or "").strip() for page in reader.pages[:MAX_PDF_PAGES]]
    except Exception:  # a damaged file must skip, never fail the whole upload
        return None
    text = "\n\n".join(p for p in pages if p)
    return text or None


def _decode(raw: bytes, name: str = "") -> Optional[str]:
    if name.lower().endswith(".pdf"):
        return _pdf_text(raw)
    if b"\x00" in raw:
        return None  # a binary file renamed to .md
    return raw.decode("utf-8-sig", errors="replace")


def _skip_reason(path: str) -> Optional[str]:
    name = _clean_name(path)
    parts = [p for p in str(path).replace("\\", "/").split("/") if p]
    if not name or any(p.startswith(".") or p == "__MACOSX" for p in parts):
        return "hidden or system file"
    if name.lower() == "readme.md":
        return "README (describes the folder, not a subject)"
    if not name.lower().endswith(TEXT_SUFFIXES):
        return "only .md, .txt, .csv and .pdf files are accepted"
    return None


def expand_archive(data: bytes) -> Tuple[List[Tuple[str, bytes]], List[Dict[str, str]]]:
    """The text entries of a zip as (name, bytes), plus what was skipped and why."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail={"code": "kb_bad_zip", "message": "This is not a valid .zip file."})
    infos = [i for i in archive.infolist() if not i.is_dir()]
    if len(infos) > settings.KB_MAX_ZIP_ENTRIES:
        raise HTTPException(status_code=413, detail={
            "code": "kb_zip_too_many_files",
            "message": f"The archive has {len(infos)} files; the limit is {settings.KB_MAX_ZIP_ENTRIES}.",
        })
    entries: List[Tuple[str, bytes]] = []
    skipped: List[Dict[str, str]] = []
    declared_total = 0
    for info in infos:
        reason = _skip_reason(info.filename)
        if reason is None and info.flag_bits & 0x1:
            reason = "encrypted"
        if reason is None and info.file_size > settings.KB_MAX_FILE_BYTES:
            reason = f"larger than {settings.KB_MAX_FILE_BYTES} bytes"
        if reason is None and declared_total + info.file_size > settings.KB_MAX_TOTAL_BYTES:
            reason = "the archive is larger than the knowledge base limit"
        if reason:
            skipped.append({"name": info.filename, "reason": reason})
            continue
        with archive.open(info) as handle:
            raw = handle.read(settings.KB_MAX_FILE_BYTES + 1)  # the declared size can lie
        if len(raw) > settings.KB_MAX_FILE_BYTES:
            skipped.append({"name": info.filename, "reason": f"larger than {settings.KB_MAX_FILE_BYTES} bytes"})
            continue
        declared_total += len(raw)
        entries.append((_clean_name(info.filename), raw))
    return entries, skipped


async def import_files(db: AsyncSession, actor_id: str, uploads: List[Tuple[str, bytes]],
                       title: Optional[str] = None) -> Dict[str, Any]:
    """Create one document per text file. ``uploads`` are (filename, bytes), zips included.

    A title typed by the admin applies only when exactly one text file is imported.
    Each document is committed on its own, so one bad file never loses the others.
    """
    if not uploads:
        raise HTTPException(status_code=422, detail={"code": "kb_no_files", "message": "Choose at least one file."})
    if len(uploads) > MAX_FILES_PER_REQUEST:
        raise HTTPException(status_code=422, detail={"code": "kb_too_many_files", "message": f"At most {MAX_FILES_PER_REQUEST} files per upload."})
    entries: List[Tuple[str, bytes]] = []
    skipped: List[Dict[str, str]] = []
    for name, raw in uploads:
        clean = _clean_name(name)
        if clean.lower().endswith(".zip"):
            found, left_out = expand_archive(raw)
            entries.extend(found)
            skipped.extend({"name": f"{clean}/{s['name']}", "reason": s["reason"]} for s in left_out)
            continue
        reason = _skip_reason(name)
        if reason:
            skipped.append({"name": name, "reason": reason})
        elif len(raw) > settings.KB_MAX_FILE_BYTES:
            skipped.append({"name": name, "reason": f"larger than {settings.KB_MAX_FILE_BYTES} bytes"})
        else:
            entries.append((clean, raw))
    if not entries:
        raise HTTPException(status_code=422, detail={
            "code": "kb_nothing_to_import",
            "message": "No .md, .txt, .csv or .pdf files were found.",
            "skipped": skipped,
        })
    created: List[Dict[str, Any]] = []
    custom_title = " ".join((title or "").split())[:200] if len(entries) == 1 else ""
    for name, raw in entries:
        text = _decode(raw, name)
        if text is None:
            skipped.append({"name": name, "reason": "no readable text (scanned or protected?)"})
            continue
        doc_title = custom_title or document_title(text, name)
        try:
            doc = await kb_service.upload(db, actor_id, doc_title, prepare_document(text), name)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            skipped.append({"name": name, "reason": detail.get("message") or detail.get("code") or "refused"})
            await db.rollback()
            continue
        created.append({"id": doc["id"], "title": doc["title"], "version": doc["version"], "chunks": doc["chunks"]})
    return {"created": created, "skipped": skipped}
