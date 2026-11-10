"""W8: the permanent ad archive copies text always and media only from Meta's CDN, within caps."""
from __future__ import annotations

import types
import uuid

import pytest
from sqlalchemy import func, select

from app.db.session import async_session_maker
from app.models.ad_archive import AdArchiveEntry
from app.models.creative import Creative
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import archive_service as svc
from app.services import safe_fetch, storage_service


def _creative(**kw):
    base = dict(platform="meta", brand_name="Acme", headline="Hi", body="Body", source_ad_id=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_archive_key_prefers_the_ad_library_id_and_is_stable_otherwise():
    assert svc.archive_key(_creative(source_ad_id="123")) == "meta:123"
    a = svc.archive_key(_creative(headline="Hi "))
    assert a == svc.archive_key(_creative(headline="hi")) and a.startswith("text:")
    assert a != svc.archive_key(_creative(body="Other"))


@pytest.mark.parametrize("url, ok", [
    ("https://scontent.xx.fbcdn.net/v/t1/abc.jpg", True),
    ("https://fbcdn.net/a.jpg", True),
    ("http://scontent.xx.fbcdn.net/a.jpg", False),          # https only
    ("https://fbcdn.net.evil.example/a.jpg", False),        # suffix trick
    ("https://evilfbcdn.net/a.jpg", False),
    ("https://127.0.0.1/a.jpg", False),
    ("https://example.com/a.jpg", False),
    (None, False),
])
def test_media_is_only_fetched_from_meta_cdn_hosts(url, ok):
    assert svc.media_host_allowed(url) is ok


@pytest.mark.asyncio
async def test_copy_media_never_fetches_disallowed_hosts(monkeypatch):
    async def boom(*_a, **_k):
        raise AssertionError("fetched")
    monkeypatch.setattr(safe_fetch, "safe_http_get_async", boom)
    assert await svc._copy_media("j", "https://example.com/a.jpg") == (None, "not_allowed", 0)
    assert await svc._copy_media("j", None) == (None, "none", 0)
    assert await svc._copy_media("j", "r2://media/x.jpg") == ("r2://media/x.jpg", "stored", 0)


@pytest.mark.asyncio
async def test_copy_media_reports_oversize_and_stores_allowed_images(monkeypatch):
    async def too_big(*_a, **_k):
        raise safe_fetch.UnsafeFetch("SSRF blocked: response exceeds 10 bytes")
    monkeypatch.setattr(safe_fetch, "safe_http_get_async", too_big)
    assert await svc._copy_media("j", "https://x.fbcdn.net/a.jpg") == (None, "too_large", 0)

    async def image(*_a, **_k):
        return types.SimpleNamespace(status_code=200, content=b"\x89PNGdata", headers={"content-type": "image/png"})
    stored = {}

    async def store(job_id, data, mime):
        stored.update(job_id=job_id, size=len(data), mime=mime)
        return "r2://media/archive.png"
    monkeypatch.setattr(safe_fetch, "safe_http_get_async", image)
    monkeypatch.setattr(storage_service, "store_media_bytes", store)
    assert await svc._copy_media("j", "https://x.fbcdn.net/a.png") == ("r2://media/archive.png", "stored", 8)
    assert stored == {"job_id": "archive_j", "size": 8, "mime": "image/png"}

    async def html(*_a, **_k):
        return types.SimpleNamespace(status_code=200, content=b"<html>", headers={"content-type": "text/html"})
    monkeypatch.setattr(safe_fetch, "safe_http_get_async", html)
    assert await svc._copy_media("j", "https://x.fbcdn.net/a.png") == (None, "failed", 0)


@pytest.mark.asyncio
async def test_archive_job_keeps_text_respects_the_cap_and_is_idempotent(monkeypatch):
    async def no_network(*_a, **_k):
        raise AssertionError("fetched")
    monkeypatch.setattr(safe_fetch, "safe_http_get_async", no_network)
    monkeypatch.setattr(svc.settings, "ARCHIVE_MAX_ENTRIES_PER_ORG", 2)
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"w8-archive-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Archive", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        job = ScrapeJob(id=f"j_{suffix}", org_id=org.id, query="archive", status="succeeded")
        db.add(job)
        await db.flush()
        for key in ("a", "b", "c"):
            db.add(Creative(id=f"c_{suffix}_{key}", job_id=job.id, brand_id="brand", brand_name="Brand",
                            platform="meta", format="image", headline=f"headline {key}", body="body",
                            source_ad_id=f"ad_{suffix}_{key}", days_active=None,
                            media_url="https://example.com/not-meta.jpg"))
        await db.commit()

        first = await svc.archive_job(db, job.id, org.id)
        assert first == {"archived": 2, "refreshed": 0, "skipped_cap": 1}
        again = await svc.archive_job(db, job.id, org.id)
        assert again == {"archived": 0, "refreshed": 2, "skipped_cap": 1}
        rows = (await db.execute(select(AdArchiveEntry).where(AdArchiveEntry.org_id == org.id))).scalars().all()
        assert len(rows) == 2
        assert all(r.media_status == "not_allowed" and r.body == "body" and r.days_active is None for r in rows)
        assert (await db.scalar(select(func.count(AdArchiveEntry.id)).where(AdArchiveEntry.org_id == org.id))) == 2

        listing = await svc.list_entries(db, user)
        assert listing["total"] == 2 and listing["cap_per_workspace"] == 2
        assert {i["source_ad_id"] for i in listing["items"]} <= {f"ad_{suffix}_a", f"ad_{suffix}_b", f"ad_{suffix}_c"}

        stranger = User(id=f"s_{suffix}", email=f"w8-archive-s-{suffix}@example.com", password_hash="x", role="member")
        db.add(stranger)
        await db.flush()
        db.add(Organization(id=f"q_{suffix}", name="Other", owner_id=stranger.id, plan="pro"))
        await db.commit()
        assert (await svc.list_entries(db, stranger))["total"] == 0
