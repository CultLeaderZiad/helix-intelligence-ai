from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Dict, Any, Optional
import re
import asyncio
import logging
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.scrape_job import ScrapeJob
from app.models.monitor import Monitor, MonitorEvent
from app.models.organization import Organization
from app.models.user import User
from app.services.ai.ai_router import MultiTierAIProvider
from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
from app.core.config import settings

logger = logging.getLogger(__name__)

def normalize_brand_name(query_or_brand: str, domain: str = None) -> str:
    """Resolve raw queries, domain names, or UUID slugs into clean, human-readable brand names."""
    val = (query_or_brand or "").strip()
    if not val and domain:
        val = domain.strip()

    if not val:
        return "Unknown Brand"

    # Strip protocols, www, and common domain extensions
    s = re.sub(r'^(https?://)?(www\.)?', '', val, flags=re.IGNORECASE)
    s = re.sub(r'\.(com|org|net|io|co|ai|app|store|shop).*$', '', s, flags=re.IGNORECASE)

    # If it is a raw UUID, fallback to domain or generic label
    if re.match(r'^[0-9a-fA-F-]{32,36}$', s):
        if domain:
            dom = re.sub(r'^(https?://)?(www\.)?', '', domain, flags=re.IGNORECASE)
            dom = re.sub(r'\.(com|org|net|io|co|ai|app|store|shop).*$', '', dom, flags=re.IGNORECASE)
            return " ".join(word.capitalize() for word in re.sub(r'[-_]+', ' ', dom).split())
        return "Ad Intelligence"

    s_lower = s.lower()
    if "gymshark" in s_lower:
        return "Gymshark"
    if "nike" in s_lower:
        return "Nike"
    if "adidas" in s_lower:
        return "Adidas"
    if "shopify" in s_lower:
        return "Shopify"
    if "allbirds" in s_lower:
        return "Allbirds"
    if "airbnb" in s_lower:
        return "Airbnb"
    if "duolingo" in s_lower:
        return "Duolingo"
    if "real madrid" in s_lower:
        return "Real Madrid"
    if "sneako" in s_lower:
        return "Sneako"
    if "andrew tate" in s_lower:
        return "Andrew Tate"
    if "cloud flare" in s_lower or "cloudflare" in s_lower:
        return "Cloudflare"
    if "linkedin" in s_lower:
        return "LinkedIn"

    # Clean punctuation / underscores and title-case
    clean = re.sub(r'[-_]+', ' ', s).strip()
    words = [w.capitalize() for w in clean.split() if w]
    return " ".join(words) if words else "Unknown Brand"


def _normalize_text_key(text: str) -> str:
    """Generates an alphanumeric key to detect duplicate headlines/bodies regardless of punctuation/spaces."""
    return re.sub(r'[^a-zA-Z0-9]+', '', (text or '').lower())


async def generate_narrative_summary(
    brand_names: List[str],
    active_ads_count: int,
    dominant_format: str,
    top_creative: Optional[Dict[str, Any]],
    monitor_changes: List[Dict[str, Any]],
    has_activity: bool
) -> Dict[str, Any]:
    """Generates an honest, grounded executive paragraph from real competitor activity."""
    if not has_activity or active_ads_count == 0:
        return {
            "status": "empty",
            "summary": None,
            "message": "Run your first search to start seeing insights here."
        }

    top_hl = (top_creative.get("headline") if top_creative else "") or "top performing creative"
    top_score = None
    if top_creative and top_creative.get("scores") and top_creative["scores"].get("composite") is not None:
        top_score = round(float(top_creative["scores"]["composite"]), 1)
    
    top_brand = top_creative.get("brand_name") if top_creative else (brand_names[0] if brand_names else "tracked brands")

    new_count = sum(1 for m in monitor_changes if m.get("type") == "new_ad")
    killed_count = sum(1 for m in monitor_changes if m.get("type") == "killed_ad")
    changed_count = sum(1 for m in monitor_changes if m.get("type") == "copy_changed")

    diff_clauses = []
    if new_count > 0:
        diff_clauses.append(f"{new_count} new competitor ad{'s' if new_count > 1 else ''} detected")
    if changed_count > 0:
        diff_clauses.append(f"{changed_count} copy alteration{'s' if changed_count > 1 else ''} recorded")
    if killed_count > 0:
        diff_clauses.append(f"{killed_count} ad{'s' if killed_count > 1 else ''} stopped")

    diff_str = ", ".join(diff_clauses) if diff_clauses else "no ad removals or copy changes recorded since last check"
    brands_str = ", ".join(brand_names[:3]) if brand_names else "tracked brands"
    score_str = f"with an ad composite score of {top_score}" if top_score else "leading the leaderboard"

    fallback_summary = (
        f"Across your tracked brands ({brands_str}), {active_ads_count} active creatives are under analysis with {dominant_format.upper()} as the dominant format. "
        f"{diff_str.capitalize() if diff_clauses else 'Tracking remains stable'}, and your highest-scoring find is '{top_hl[:65]}' by {top_brand} ({score_str})."
    )

    try:
        provider = MultiTierAIProvider()
        prompt = f"""Write a single concise executive paragraph (2-3 sentences max) summarizing recent competitor movements based strictly on this factual data:
- Tracked Brands: {brands_str}
- Total Active Creatives Analyzed: {active_ads_count}
- Dominant Format: {dominant_format}
- Monitor Diff Events: {diff_str}
- Highest-Scoring Creative: "{top_hl[:80]}" by {top_brand} ({score_str})

STRICT HONESTY RULES:
- Do not invent numbers, brands, or events not present in the data.
- If there are no monitor diffs, state that tracking is stable without inventing diffs.
- Plain language only. No marketing buzzwords or exaggeration."""

        res = await asyncio.wait_for(
            provider._call_api([
                {"role": "system", "content": "You are an objective competitive ad analyst for Helix. Reply with plain text only."},
                {"role": "user", "content": prompt}
            ]),
            timeout=3.5
        )
        clean_res = res.strip().replace('"', '').replace('\n', ' ')
        if len(clean_res) > 30 and "{" not in clean_res:
            return {
                "status": "ready",
                "summary": clean_res,
                "message": None
            }
    except Exception as e:
        logger.debug(f"AI narrative summary used deterministic fallback: {e}")

    return {
        "status": "ready",
        "summary": fallback_summary,
        "message": None
    }


async def get_dashboard_metrics(db: AsyncSession, user: Optional[User] = None) -> Dict[str, Any]:
    if settings.USE_MOCKS:
        return {
            "narrative_summary": {
                "status": "empty",
                "summary": None,
                "message": "Run your first search to start seeing insights here."
            },
            "has_monitors": False,
            "active_monitors_count": 0,
            "monitor_changes": [],
            "top_performers": [],
            "reach_leaderboard": [],
            "timeline": [],
            "cross_brand": []
        }

    # 1. Top Performers: Creatives sorted by composite score
    # Join with ScrapeJob to retrieve real brand query, filter out empty/template rows
    top_query = (
        select(Creative, CreativeScore, ScrapeJob.query)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .outerjoin(ScrapeJob, Creative.job_id == ScrapeJob.id)
        .where(CreativeScore.composite.isnot(None))
        .where(Creative.headline.isnot(None))
        .where(Creative.headline != "")
        .where(~Creative.headline.ilike("%{{product.brand%"))
        .where(~Creative.headline.ilike("%{{page.name%"))
        .order_by(desc(CreativeScore.composite))
        .limit(60)
    )
    top_result = await db.execute(top_query)
    top_rows = top_result.all()

    # Deduplicate distinct winning creatives so repeated test scrapes don't saturate top 10
    distinct_top = []
    seen_top_keys = set()
    for c, score, job_query in top_rows:
        key = _normalize_text_key(c.headline)
        if key in seen_top_keys or len(key) < 4:
            continue
        seen_top_keys.add(key)
        distinct_top.append((c, score, job_query))
        if len(distinct_top) >= 10:
            break

    top_performers = _map_creatives(distinct_top)

    # 2. Reach/Activity Leaderboard: Sorted by impressions_est or days_active
    reach_query = (
        select(Creative, CreativeScore, ScrapeJob.query)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .outerjoin(ScrapeJob, Creative.job_id == ScrapeJob.id)
        .where(Creative.headline.isnot(None))
        .where(Creative.headline != "")
        .where(~Creative.headline.ilike("%{{product.brand%"))
        .where(~Creative.headline.ilike("%{{page.name%"))
        .order_by(desc(func.coalesce(Creative.impressions_est, 0)), desc(Creative.days_active))
        .limit(60)
    )
    reach_result = await db.execute(reach_query)
    reach_rows = reach_result.all()

    # Deduplicate distinct creatives
    distinct_reach = []
    seen_reach_keys = set()
    for c, score, job_query in reach_rows:
        key = _normalize_text_key(c.headline)
        if key in seen_reach_keys or len(key) < 4:
            continue
        seen_reach_keys.add(key)
        distinct_reach.append((c, score, job_query))
        if len(distinct_reach) >= 10:
            break

    reach_leaderboard = _map_creatives(distinct_reach)

    # 3. Timeline View: Jobs/Creatives over time
    timeline_query = (
        select(
            func.date(ScrapeJob.created_at).label("date"),
            func.count(Creative.id).label("creative_count")
        )
        .outerjoin(Creative, Creative.job_id == ScrapeJob.id)
        .group_by(func.date(ScrapeJob.created_at))
        .order_by(func.date(ScrapeJob.created_at))
    )
    timeline_result = await db.execute(timeline_query)
    timeline_rows = timeline_result.all()
    
    timeline = [{"date": str(row.date), "count": row.creative_count} for row in timeline_rows if row.date]

    # 4. Cross-Brand Comparison: Aggregated metrics per REAL resolved brand
    brand_data_query = (
        select(
            Creative.id,
            Creative.brand_id,
            Creative.landing_domain,
            Creative.format,
            CreativeScore.composite,
            ScrapeJob.query.label("job_query")
        )
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .outerjoin(ScrapeJob, Creative.job_id == ScrapeJob.id)
        .where(Creative.headline.isnot(None))
        .where(Creative.headline != "")
        .where(~Creative.headline.ilike("%{{product.brand%"))
    )
    brand_data_result = await db.execute(brand_data_query)
    all_brand_rows = brand_data_result.all()

    # Group by resolved brand name
    brand_aggregates = {}
    for row in all_brand_rows:
        resolved_name = normalize_brand_name(row.job_query or row.brand_id, row.landing_domain)
        if resolved_name in ("Unknown Brand", "Ad Intelligence", "*"):
            continue

        slug = resolved_name.lower().replace(" ", "-")
        if slug not in brand_aggregates:
            brand_aggregates[slug] = {
                "brand_id": slug,
                "name": resolved_name,
                "creatives": set(),
                "scores": [],
                "formats": {}
            }

        brand_aggregates[slug]["creatives"].add(row.id)
        if row.composite is not None:
            brand_aggregates[slug]["scores"].append(float(row.composite))
        fmt = (row.format or "image").lower()
        brand_aggregates[slug]["formats"][fmt] = brand_aggregates[slug]["formats"].get(fmt, 0) + 1

    cross_brand = []
    for slug, bdata in brand_aggregates.items():
        scores = bdata["scores"]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        
        # Determine dominant format
        formats = bdata["formats"]
        dominant_format = max(formats.items(), key=lambda x: x[1])[0] if formats else "image"

        cross_brand.append({
            "brand_id": bdata["brand_id"],
            "name": bdata["name"],
            "active_ads": len(bdata["creatives"]),
            "avg_score": avg_score,
            "dominant_format": dominant_format
        })

    # Sort cross-brand comparison by active_ads descending so leading brands appear first
    cross_brand.sort(key=lambda b: b["active_ads"], reverse=True)

    # 5. Monitor events & changes
    monitor_changes = []
    active_monitors_count = 0
    has_monitors = False

    org_id = None
    if user:
        try:
            from app.services.billing_service import get_or_create_default_org
            org = await get_or_create_default_org(db, user)
            org_id = org.id
        except Exception as exc:
            logger.debug(f"Could not get org for dashboard user: {exc}")

    try:
        from app.services.monitor_service import serialize_event
        if org_id:
            m_count_res = await db.execute(
                select(func.count(Monitor.id)).where(Monitor.org_id == org_id)
            )
            active_monitors_count = m_count_res.scalar() or 0
            has_monitors = active_monitors_count > 0

            events_query = (
                select(MonitorEvent, Monitor.name.label("monitor_name"), Monitor.query.label("monitor_query"))
                .join(Monitor, Monitor.id == MonitorEvent.monitor_id)
                .where(Monitor.org_id == org_id)
                .order_by(MonitorEvent.created_at.desc())
                .limit(20)
            )
            events_result = await db.execute(events_query)
            for row in events_result.all():
                ev = row[0]
                m_name = row[1]
                m_query = row[2]
                event_dict = serialize_event(ev)
                event_dict["monitor_name"] = m_name or m_query or "Tracked Competitor"
                monitor_changes.append(event_dict)
        else:
            m_count_res = await db.execute(select(func.count(Monitor.id)))
            active_monitors_count = m_count_res.scalar() or 0
            has_monitors = active_monitors_count > 0

            events_query = (
                select(MonitorEvent, Monitor.name.label("monitor_name"), Monitor.query.label("monitor_query"))
                .join(Monitor, Monitor.id == MonitorEvent.monitor_id)
                .order_by(MonitorEvent.created_at.desc())
                .limit(20)
            )
            events_result = await db.execute(events_query)
            for row in events_result.all():
                ev = row[0]
                m_name = row[1]
                m_query = row[2]
                event_dict = serialize_event(ev)
                event_dict["monitor_name"] = m_name or m_query or "Tracked Competitor"
                monitor_changes.append(event_dict)
    except Exception as e:
        logger.warning(f"Failed to fetch monitor events for dashboard: {e}")

    # 6. Generate grounded narrative summary
    top_creatives_dicts = [c.dict() for c in top_performers]
    top_creative = top_creatives_dicts[0] if top_creatives_dicts else None
    tracked_brand_names = [b["name"] for b in cross_brand]
    total_active_creatives = sum(b["active_ads"] for b in cross_brand)
    dominant_format = cross_brand[0]["dominant_format"] if cross_brand else "video"
    has_activity = bool(all_brand_rows or monitor_changes or timeline)

    narrative_summary = await generate_narrative_summary(
        brand_names=tracked_brand_names,
        active_ads_count=total_active_creatives,
        dominant_format=dominant_format,
        top_creative=top_creative,
        monitor_changes=monitor_changes,
        has_activity=has_activity
    )

    return {
        "narrative_summary": narrative_summary,
        "has_monitors": has_monitors,
        "active_monitors_count": active_monitors_count,
        "monitor_changes": monitor_changes,
        "top_performers": top_creatives_dicts,
        "reach_leaderboard": [c.dict() for c in reach_leaderboard],
        "timeline": timeline,
        "cross_brand": cross_brand
    }


def _map_creatives(rows):
    items = []
    for row in rows:
        c = row[0]
        score = row[1]
        job_query = row[2] if len(row) > 2 else None

        resolved_name = normalize_brand_name(job_query or c.brand_id, c.landing_domain)
        resolved_slug = resolved_name.lower().replace(" ", "-")

        items.append(CreativeSchema(
            id=c.id,
            brand_id=resolved_slug,
            brand_name=resolved_name,
            platform=c.platform,
            format=c.format,
            source_type=getattr(c, "data_source", "ad") or "ad",
            headline=c.headline or "",
            body=c.body or "",
            cta=c.cta or "",
            landing_domain=c.landing_domain,
            thumbnail_ratio=c.thumbnail_ratio,
            duration_seconds=c.duration_seconds,
            first_seen=c.first_seen or "",
            last_seen=c.last_seen or "",
            days_active=c.days_active or 1,
            variant_count=c.variant_count or 1,
            scores=Scores(
                hook=score.hook if score else None,
                clarity=score.clarity if score else None,
                retention=score.retention if score else None,
                composite=score.composite if score else None
            ) if score else Scores(),
            metrics=CreativeMetrics(
                impressions_est=c.impressions_est,
                is_impression_estimate=getattr(c, "is_estimated", True),
                spend_band=c.spend_band,
                engagement_rate=c.engagement_rate,
                ctr_est=c.ctr_est
            ),
            pattern_ids=[]
        ))
    return items

