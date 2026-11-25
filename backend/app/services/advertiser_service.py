"""Advertiser page and winner signals. Database only: no provider call, no cost.

Everything here comes from rows the workspace already has:
- ``creatives`` from its own searches (scoped through scrape_jobs.org_id);
- ``monitor_creatives`` from its own monitors (launch dates, active/killed).

There is no combined "winner score". Each ad gets its real components:
- ``days_active``: from the ad's own dates; ``None`` (unknown) when the
  provider gave none, never 0;
- ``variants``: ads of this advertiser with the same fingerprint identity
  (same platform, domain, format and anchor copy) but different copy;
- ``landing_page_reuse``: this advertiser's ads pointing at the same domain;
- the advertiser's ``launches_last_30d`` seen by your monitors.
Ads are listed by days_active (unknown last), then variants, then reuse.
"""
from __future__ import annotations

import datetime
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative import Creative
from app.models.monitor import Monitor, MonitorCreative
from app.models.scrape_job import ScrapeJob
from app.services.creative_fingerprint import normalize_domain, signature_for
from app.services.query_bounds import pagination_bounds

MAX_ROWS = 3000  # per advertiser; a page never scans more than this
WEEKS = 12
BASELINE_GRACE = datetime.timedelta(minutes=5)


def _parse_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def days_active(c: Creative) -> Optional[int]:
    if c.days_active is not None and c.days_active >= 0:
        return int(c.days_active)
    start, end = _parse_date(c.first_seen), _parse_date(c.last_seen)
    if start and end and end >= start:
        return (end - start).days + 1
    return None


async def _creatives(db: AsyncSession, scope: Optional[List[str]], brand_id: str) -> List[Creative]:
    stmt = select(Creative).join(ScrapeJob, ScrapeJob.id == Creative.job_id).where(Creative.brand_id == brand_id)
    if scope is not None:
        stmt = stmt.where(ScrapeJob.org_id.in_(scope or [""]))
    rows = (await db.execute(stmt.order_by(Creative.fetched_at.desc().nulls_last()).limit(MAX_ROWS))).scalars().all()
    # The same ad found by several searches is one ad: keep its newest row.
    unique: Dict[str, Creative] = {}
    for c in rows:
        key = c.source_ad_id or _sig(c).identity + ":" + _sig(c).content
        unique.setdefault(key, c)
    return list(unique.values())


def _sig(c: Creative):
    return signature_for(platform=c.platform, format=c.format, headline=c.headline, body=c.body,
                         cta=c.cta, landing_domain=c.landing_domain, creative_id=c.id)


async def _monitored(db: AsyncSession, scope: Optional[List[str]], brand_id: str):
    stmt = (
        select(MonitorCreative, Monitor.baseline_at)
        .join(Monitor, Monitor.id == MonitorCreative.monitor_id)
        .join(Creative, Creative.id == MonitorCreative.creative_id)
        .where(Creative.brand_id == brand_id)
    )
    if scope is not None:
        stmt = stmt.where(Monitor.org_id.in_(scope or [""]))
    return (await db.execute(stmt.limit(MAX_ROWS))).all()


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def components(ads: List[Creative]) -> Dict[str, Dict[str, Any]]:
    sigs = {c.id: _sig(c) for c in ads}
    contents_by_identity: Dict[str, set] = defaultdict(set)
    for s in sigs.values():
        contents_by_identity[s.identity].add(s.content)
    domains = Counter(normalize_domain(c.landing_domain) for c in ads if c.landing_domain)
    out = {}
    for c in ads:
        s = sigs[c.id]
        dom = normalize_domain(c.landing_domain) if c.landing_domain else ""
        out[c.id] = {
            "days_active": days_active(c),
            "variants": len(contents_by_identity[s.identity]),
            "landing_page_reuse": domains[dom] if dom else None,
            "fingerprint_anchor": s.anchor,
        }
    return out


async def landing_domain(db: AsyncSession, scope: Optional[List[str]], brand_id: str) -> Optional[str]:
    """The website most of this advertiser's ads in the workspace point to (404 when it has no ads here)."""
    from app.services.competitor_snapshot import top_domain

    ads = await _creatives(db, scope, brand_id)
    if not ads:
        raise HTTPException(status_code=404, detail="No ads from this advertiser in your workspace yet.")
    return top_domain([c.landing_domain for c in ads])


async def summary(db: AsyncSession, scope: Optional[List[str]], brand_id: str) -> Dict[str, Any]:
    ads = await _creatives(db, scope, brand_id)
    monitored = await _monitored(db, scope, brand_id)
    if not ads and not monitored:
        raise HTTPException(status_code=404, detail="No ads from this advertiser in your workspace yet.")
    now = datetime.datetime.now(datetime.timezone.utc)
    week0 = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weeks = [week0 - datetime.timedelta(weeks=i) for i in range(WEEKS - 1, -1, -1)]
    launches = [0] * WEEKS
    active = [0] * WEEKS
    launches_30d = 0
    active_now = 0
    for mc, baseline_at in monitored:
        first, last = _aware(mc.first_seen_at), _aware(mc.last_seen_at)
        is_launch = not (baseline_at and first <= _aware(baseline_at) + BASELINE_GRACE)
        if mc.status == "active":
            active_now += 1
        if is_launch and first >= now - datetime.timedelta(days=30):
            launches_30d += 1
        for i, start in enumerate(weeks):
            end = start + datetime.timedelta(weeks=1)
            if is_launch and start <= first < end:
                launches[i] += 1
            if first < end and (mc.status == "active" or last >= start):
                active[i] += 1
    known_days = [d for d in (days_active(c) for c in ads) if d is not None]
    names = Counter(c.brand_name for c in ads if c.brand_name)
    return {
        "brand_id": brand_id,
        "brand_name": names.most_common(1)[0][0] if names else None,
        "ads_found": len(ads),
        "ads_with_known_run_length": len(known_days),
        "longest_running_days": max(known_days) if known_days else None,
        "monitored_ads": len(monitored),
        "active_now": active_now if monitored else None,
        "launches_last_30d": launches_30d if monitored else None,
        "weekly": [
            {"week_start": w.date().isoformat(), "launches": launches[i], "active": active[i]} for i, w in enumerate(weeks)
        ] if monitored else [],
        "source_note": "Launches and active counts come only from your monitors; baseline ads are not counted as launches.",
    }


async def winners(db: AsyncSession, scope: Optional[List[str]], brand_id: str, page: int, page_size: int) -> Dict[str, Any]:
    offset, page_size = pagination_bounds(page, page_size)
    ads = await _creatives(db, scope, brand_id)
    comps = components(ads)

    def key(c: Creative):
        comp = comps[c.id]
        known = comp["days_active"] is not None
        return (not known, -(comp["days_active"] or 0), -comp["variants"], -(comp["landing_page_reuse"] or 0))

    ordered = sorted(ads, key=key)
    items = [{
        "id": c.id, "headline": c.headline, "body": (c.body or "")[:400], "cta": c.cta, "format": c.format,
        "platform": c.platform, "landing_domain": c.landing_domain, "thumbnail_url": c.thumbnail_url,
        "permalink": c.permalink, "first_seen": c.first_seen, "last_seen": c.last_seen,
        "signals": comps[c.id],
    } for c in ordered[offset:offset + page_size]]
    return {"items": items, "total": len(ordered), "page": page, "page_size": page_size,
            "has_more": offset + page_size < len(ordered),
            "order": "days_active desc (unknown last), then variants, then landing_page_reuse"}
