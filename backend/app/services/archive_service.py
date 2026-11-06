"""Permanent ad archive: copy text and media of every ad Discover finds.

Runs as its own ``archive`` work item after a Discover search succeeds, so
downloading media never slows the search. Rules:

* text is always archived (it is small and is the part that disappears);
* media is downloaded only over https from Meta's own CDN hosts
  (ARCHIVE_MEDIA_HOST_SUFFIXES), through safe_fetch (no private addresses),
  and only up to ARCHIVE_MAX_MEDIA_BYTES; otherwise ``media_status`` says why;
* media lands where every other upload lands: private R2 when configured,
  else the guarded local uploads directory;
* each workspace keeps at most ARCHIVE_MAX_ENTRIES_PER_ORG entries; past the
  cap new ads are not archived (existing entries are still refreshed).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ad_archive import AdArchiveEntry
from app.models.creative import Creative
from app.models.scrape_job import ScrapeJob

logger = logging.getLogger(__name__)

_ALLOWED_MEDIA_TYPES = ("image/", "video/")


def archive_key(creative) -> str:
    if getattr(creative, "source_ad_id", None):
        return f"{creative.platform}:{creative.source_ad_id}"
    digest = hashlib.sha256("|".join([
        creative.platform or "",
        (creative.brand_name or "").lower().strip(),
        (creative.headline or "").lower().strip(),
        (creative.body or "").lower().strip()[:500],
    ]).encode("utf-8")).hexdigest()[:32]
    return f"text:{digest}"


def media_host_allowed(url: Optional[str]) -> bool:
    if not url:
        return False
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in settings.ARCHIVE_MEDIA_HOST_SUFFIXES)


async def _copy_media(job_id: str, url: Optional[str]) -> tuple[Optional[str], str, int]:
    """Return (stored_ref, status, bytes)."""
    if not url:
        return None, "none", 0
    if url.startswith(("r2://", "/uploads/")):
        return url, "stored", 0  # already re-hosted by an earlier step
    if not media_host_allowed(url):
        return None, "not_allowed", 0
    from app.services.safe_fetch import UnsafeFetch, safe_http_get_async
    from app.services.storage_service import store_media_bytes

    limit = int(settings.ARCHIVE_MAX_MEDIA_BYTES)
    try:
        response = await safe_http_get_async(url, timeout=30.0, max_bytes=limit + 1)
    except UnsafeFetch as exc:
        # safe_fetch reports an oversize body the same way as a blocked host.
        return None, ("too_large" if "exceeds" in str(exc) else "not_allowed"), 0
    except Exception:  # network errors
        logger.info("archive media fetch failed for job %s", job_id)
        return None, "failed", 0
    if response.status_code >= 400:
        return None, "failed", 0
    content = response.content or b""
    if len(content) > limit:
        return None, "too_large", 0
    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    if not content or not content_type.startswith(_ALLOWED_MEDIA_TYPES):
        return None, "failed", 0
    ref = await store_media_bytes(f"archive_{job_id}", content, content_type)
    return ref, "stored", len(content)


async def archive_job(db: AsyncSession, job_id: str, org_id: str) -> dict:
    """Archive every creative of one succeeded Discover job. Idempotent."""
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id, ScrapeJob.org_id == org_id))).scalar_one_or_none()
    if job is None or job.status != "succeeded":
        return {"archived": 0, "refreshed": 0, "skipped_cap": 0}
    creatives = (await db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()
    count = await db.scalar(select(func.count(AdArchiveEntry.id)).where(AdArchiveEntry.org_id == org_id)) or 0
    cap = int(settings.ARCHIVE_MAX_ENTRIES_PER_ORG)
    archived = refreshed = skipped_cap = 0
    now = datetime.now(timezone.utc)
    for creative in creatives:
        key = archive_key(creative)
        entry = (await db.execute(select(AdArchiveEntry).where(
            AdArchiveEntry.org_id == org_id, AdArchiveEntry.archive_key == key
        ))).scalar_one_or_none()
        if entry is None:
            if count >= cap:
                skipped_cap += 1
                continue
            entry = AdArchiveEntry(org_id=org_id, archive_key=key, platform=creative.platform or "meta")
            db.add(entry)
            count += 1
            archived += 1
        else:
            refreshed += 1
        entry.creative_id = creative.id
        entry.job_id = job_id
        entry.source_ad_id = creative.source_ad_id
        entry.brand_name = creative.brand_name
        entry.format = creative.format
        entry.headline = creative.headline
        entry.body = creative.body
        entry.cta = creative.cta
        entry.landing_domain = creative.landing_domain
        entry.permalink = creative.permalink
        entry.first_seen = entry.first_seen or creative.first_seen
        entry.last_seen = creative.last_seen
        entry.days_active = creative.days_active
        entry.updated_at = now
        if entry.media_status != "stored":
            entry.original_media_url = creative.media_url
            entry.original_thumbnail_url = creative.thumbnail_url
            media_ref, media_status, media_bytes = await _copy_media(job_id, creative.media_url)
            thumb_ref, thumb_status, thumb_bytes = await _copy_media(job_id, creative.thumbnail_url)
            entry.media_ref = media_ref
            entry.thumbnail_ref = thumb_ref
            entry.media_bytes = media_bytes + thumb_bytes
            entry.media_status = "stored" if (media_ref or thumb_ref) else (
                media_status if media_status != "none" else thumb_status
            )
        await db.flush()
    await db.commit()
    if skipped_cap:
        logger.warning("ad archive cap reached for org %s: %s ads not archived", org_id, skipped_cap)
    return {"archived": archived, "refreshed": refreshed, "skipped_cap": skipped_cap}


def entry_view(entry: AdArchiveEntry) -> dict:
    from app.services.storage_service import resolve_stored_url

    def media(ref):
        try:
            return resolve_stored_url(ref)
        except RuntimeError:
            return None

    return {
        "id": entry.id,
        "creative_id": entry.creative_id,
        "platform": entry.platform,
        "source_ad_id": entry.source_ad_id,
        "brand_name": entry.brand_name,
        "format": entry.format,
        "headline": entry.headline or "",
        "body": entry.body or "",
        "cta": entry.cta or "",
        "landing_domain": entry.landing_domain,
        "permalink": entry.permalink,
        "first_seen": entry.first_seen,
        "last_seen": entry.last_seen,
        "days_active": entry.days_active,
        "media_url": media(entry.media_ref),
        "thumbnail_url": media(entry.thumbnail_ref),
        "media_status": entry.media_status,
        "archived_at": entry.archived_at.isoformat() if entry.archived_at else None,
    }


async def _org_ids(db: AsyncSession, user) -> list[str]:
    from app.core.tenancy import get_user_org_ids

    org_ids = await get_user_org_ids(db, user)
    if org_ids is None:  # platform admin: their own workspace only, never all tenants
        from app.services.billing_service import resolve_active_org

        org = await resolve_active_org(db, user)
        return [org.id] if org else []
    return org_ids


async def list_entries(db: AsyncSession, user, *, page: int = 1, page_size: int = 50, brand: Optional[str] = None) -> dict:
    from app.services.query_bounds import pagination_bounds

    org_ids = await _org_ids(db, user)
    offset, page_size = pagination_bounds(page, page_size)
    filters = [AdArchiveEntry.org_id.in_(org_ids or [""])]
    if brand:
        filters.append(func.lower(AdArchiveEntry.brand_name) == brand.strip().lower())
    total = await db.scalar(select(func.count(AdArchiveEntry.id)).where(*filters)) or 0
    rows = (await db.execute(
        select(AdArchiveEntry).where(*filters)
        .order_by(AdArchiveEntry.archived_at.desc(), AdArchiveEntry.id)
        .offset(offset).limit(page_size)
    )).scalars().all()
    return {
        "items": [entry_view(e) for e in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": offset + page_size < total,
        "cap_per_workspace": int(settings.ARCHIVE_MAX_ENTRIES_PER_ORG),
    }


async def get_for_creative(db: AsyncSession, user, creative_id: str) -> dict:
    org_ids = await _org_ids(db, user)
    entry = (await db.execute(select(AdArchiveEntry).where(
        AdArchiveEntry.creative_id == creative_id, AdArchiveEntry.org_id.in_(org_ids or [""])
    ))).scalars().first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not archived")
    return entry_view(entry)
