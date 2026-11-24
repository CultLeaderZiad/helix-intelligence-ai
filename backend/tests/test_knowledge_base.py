"""3.4 Knowledge base: chunking, versions, search, limits, audit, merge script."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.knowledge_base import KbAudit, KbDocument
from app.models.user import User
from app.services import kb_service
from scripts import kb_merge


async def _admin():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        db.add(User(id=f"u_kb_{s}", email=f"kb-{s}@example.com", password_hash="x", role="admin"))
        await db.commit()
    return f"u_kb_{s}", s


def test_chunker_splits_on_headings_and_bounds_size():
    body = "# Hooks\n\n" + "A hook grabs attention. " * 10 + "\n\n# Offers\n\nShow the price.\n\n" + "x" * 5000
    parts = kb_service.chunk_text(body)
    assert parts[0].startswith("# Hooks") and any(p.startswith("# Offers") for p in parts)
    assert all(len(p) <= kb_service.CHUNK_MAX for p in parts)


@pytest.mark.asyncio
async def test_upload_versions_search_and_audit():
    actor, s = await _admin()
    title = f"Ad playbook {s}"
    async with async_session_maker() as db:
        v1 = await kb_service.upload(db, actor, title, f"# Hooks\n\nUse a question hook zebra{s} in the first line.")
        v2 = await kb_service.upload(db, actor, title, f"# Hooks\n\nUse a bold claim hook giraffe{s} in the first line.",
                                     filename="playbook.md")
        assert (v1["version"], v2["version"]) == (1, 2)
        with pytest.raises(HTTPException) as exc:  # same content again
            await kb_service.upload(db, actor, title, f"# Hooks\n\nUse a bold claim hook giraffe{s} in the first line.")
        assert exc.value.status_code == 409

        # Only the enabled (latest) version is searchable, with a citation.
        assert await kb_service.search(db, f"zebra{s}") == []
        hits = await kb_service.search(db, f"giraffe{s}")
        assert hits and hits[0]["title"] == title and hits[0]["version"] == 2 and hits[0]["chunk_id"]

        await kb_service.set_status(db, actor, v2["id"], False)
        assert await kb_service.search(db, f"giraffe{s}") == []
        await kb_service.delete(db, actor, v1["id"])
        actions = [a.action for a in (await db.execute(
            select(KbAudit).where(KbAudit.title == title).order_by(KbAudit.created_at))).scalars().all()]
        assert actions == ["upload", "upload", "disable", "delete"]


@pytest.mark.asyncio
async def test_arabic_text_is_searchable():
    actor, s = await _admin()
    async with async_session_maker() as db:
        await kb_service.upload(db, actor, f"عربي {s}", f"استخدم العروض المحدودة لزيادة المبيعات في رمضان {s}")
        hits = await kb_service.search(db, "العروض المحدودة")
    assert any(h["title"] == f"عربي {s}" for h in hits)


@pytest.mark.asyncio
async def test_size_limits_and_file_type(monkeypatch):
    actor, s = await _admin()
    monkeypatch.setattr(settings, "KB_MAX_FILE_BYTES", 100)
    async with async_session_maker() as db:
        with pytest.raises(HTTPException) as exc:
            await kb_service.upload(db, actor, f"big {s}", "x" * 200)
        assert exc.value.status_code == 413
        with pytest.raises(HTTPException) as exc:
            await kb_service.upload(db, actor, f"pdf {s}", "text", filename="a.pdf")
        assert exc.value.detail["code"] == "kb_file_type"
        assert (await db.execute(select(KbDocument).where(KbDocument.title.like(f"% {s}")))).scalars().all() == []


def test_merge_script_dedupes_and_drops_noise_without_rewriting():
    a = "# Hooks\n\nOpen with the customer's problem, not your product name.\n\nTable of contents\n\nhttps://example.com\n\nok"
    b = "Open with the customer's PROBLEM — not your product name!\n\n# Offers\n\nState the price and what is included in plain words."
    text, dropped = kb_merge.merge([("a.md", a), ("b.txt", b)])
    assert text.count("Open with the customer") == 1
    assert "State the price and what is included in plain words." in text
    assert "<!-- source: a.md -->" in text and "<!-- source: b.txt -->" in text
    assert dropped["duplicate"] == 1 and dropped["links only"] == 1 and dropped["too short"] == 1
    assert dropped["navigation/boilerplate"] == 1
