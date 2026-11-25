"""Knowledge-base file and zip import, through the real HTTP endpoint as a full admin."""
import io
import uuid
import zipfile

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import async_session_maker
from app.main import app
from app.models.knowledge_base import KbChunk, KbDocument
from app.models.user import User
from app.services import kb_import, kb_service

ARTICLE = ("---\ntitle: {title}\nslug: {slug}\ncategory: ad-creative\ntags: [hooks, copy]\n"
           "summary: How to open an ad so the right person keeps reading past the first line.\nlevel: beginner\n"
           "updated: 2026-11-24\nsources:\n  - \"A talk about hooks\"\n---\n# {title}\n\n"
           "Open with the customer's problem and not with your product name. Marker {marker}.\n")


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return buffer.getvalue()


async def _admin():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        db.add(User(id=f"u_kbi_{s}", email=f"kbi-{s}@example.com", password_hash=get_password_hash("x"), role="admin", is_platform_admin=True))
        await db.commit()
    token = create_access_token(subject=f"u_kbi_{s}")
    return s, {"Authorization": f"Bearer {token}"}


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")


async def _post(headers, files, data=None):
    async with _client() as client:
        return await client.post("/api/admin/knowledge-base/upload", headers=headers, files=files, data=data or {})


@pytest.mark.asyncio
async def test_zip_becomes_one_document_per_article_with_front_matter_cleaned():
    s, headers = await _admin()
    marker = f"zebra{s}"
    archive = _zip({
        "kb/README.md": "# About this folder\n\nUpload these files as they are.",
        "kb/ad-creative/hooks-a.md": ARTICLE.format(title=f"Hooks A {s}", slug="a", marker=marker),
        "kb/ad-creative/hooks-b.md": ARTICLE.format(title=f"Hooks B {s}", slug="b", marker=marker + "b"),
        "kb/notes.txt": f"Plain notes {s}: measure your own baseline before changing anything about the offer.",
        "kb/logo.png": "not text",
        "kb/.hidden.md": "# hidden",
        "__MACOSX/kb/._hooks-a.md": "junk",
    })
    response = await _post(headers, [("files", ("kb.zip", archive, "application/zip"))])
    assert response.status_code == 201, response.text
    body = response.json()
    assert sorted(d["title"] for d in body["created"]) == sorted([f"Hooks A {s}", f"Hooks B {s}", f"Notes"])
    reasons = {x["name"].split("/")[-1]: x["reason"] for x in body["skipped"]}
    assert "README" in reasons["README.md"] and reasons["logo.png"] == "only .md, .txt, .csv and .pdf files are accepted"
    assert reasons[".hidden.md"] == "hidden or system file"

    async with async_session_maker() as db:
        hit = await kb_service.search(db, marker)
        assert hit and hit[0]["title"] == f"Hooks A {s}"        # cited by its own article title
        doc = (await db.execute(select(KbDocument).where(KbDocument.title == f"Hooks A {s}"))).scalar_one()
        text = " ".join(c.text for c in (await db.execute(select(KbChunk).where(KbChunk.document_id == doc.id))).scalars())
        assert "slug:" not in text and "level:" not in text and "updated:" not in text
        assert "Tags: hooks, copy" in text and "Sources: A talk about hooks" in text
        assert "Open with the customer's problem" in text      # the article is kept as written


@pytest.mark.asyncio
async def test_single_files_title_override_and_unchanged_reupload():
    s, headers = await _admin()
    first = await _post(headers, [("files", ("a.md", f"# Offers {s}\n\nState the price and what is included, in plain words.".encode(), "text/markdown"))],
                        data={"title": f"My title {s}"})
    assert first.status_code == 201 and first.json()["created"][0]["title"] == f"My title {s}"
    again = await _post(headers, [("files", ("a.md", f"# Offers {s}\n\nState the price and what is included, in plain words.".encode(), "text/markdown"))],
                        data={"title": f"My title {s}"})
    assert again.status_code == 201 and again.json()["created"] == []   # nothing new: reported, not duplicated
    assert "already uploaded" in again.json()["skipped"][0]["reason"]
    changed = await _post(headers, [("files", ("a.md", f"# Offers {s}\n\nState the price, the guarantee and what is included.".encode(), "text/markdown"))],
                          data={"title": f"My title {s}"})
    assert changed.json()["created"][0]["version"] == 2


@pytest.mark.asyncio
async def test_bad_zip_binary_and_oversize_files_are_refused_with_reasons(monkeypatch):
    s, headers = await _admin()
    bad = await _post(headers, [("files", ("x.zip", b"this is not a zip", "application/zip"))])
    assert bad.status_code == 422 and bad.json()["detail"]["code"] == "kb_bad_zip"

    binary = await _post(headers, [("files", ("fake.md", b"abc\x00def", "text/markdown"))])
    assert binary.status_code == 201 and binary.json()["created"] == [] and binary.json()["skipped"][0]["reason"] == "not a text file"

    monkeypatch.setattr(settings, "KB_MAX_FILE_BYTES", 200)
    big = await _post(headers, [("files", ("big.md", b"x" * 500, "text/markdown"))])
    assert big.status_code == 413

    archive = _zip({"ok.md": f"# Small {s}\n\nA short but real piece of guidance about testing one change at a time.", "huge.md": "y" * 5000})
    mixed = await _post(headers, [("files", ("m.zip", archive, "application/zip"))])
    body = mixed.json()
    assert [d["title"] for d in body["created"]] == ["Ok"] and "larger than" in body["skipped"][0]["reason"]


@pytest.mark.asyncio
async def test_zip_entry_count_limit_and_non_admins(monkeypatch):
    s, headers = await _admin()
    monkeypatch.setattr(settings, "KB_MAX_ZIP_ENTRIES", 3)
    many = _zip({f"f{i}.md": f"# T{i}\n\nbody {i} {s}" for i in range(5)})
    response = await _post(headers, [("files", ("many.zip", many, "application/zip"))])
    assert response.status_code == 413 and response.json()["detail"]["code"] == "kb_zip_too_many_files"

    async with async_session_maker() as db:
        db.add(User(id=f"u_member_{s}", email=f"member-{s}@example.com", password_hash=get_password_hash("x"), role="member"))
        await db.commit()
    member = {"Authorization": f"Bearer {create_access_token(subject=f'u_member_{s}')}"}
    denied = await _post(member, [("files", ("a.md", b"# A\n\nbody", "text/markdown"))])
    assert denied.status_code in (401, 403)


def test_front_matter_helpers():
    meta, sources, rest = kb_import.split_front_matter(ARTICLE.format(title="T", slug="s", marker="m"))
    assert meta["title"] == "T" and sources == ["A talk about hooks"] and rest.startswith("# T")
    assert kb_import.document_title("no front matter here", "creative-fatigue.md") == "Creative fatigue"
    assert kb_import.prepare_document("plain text stays as it is") == "plain text stays as it is"
