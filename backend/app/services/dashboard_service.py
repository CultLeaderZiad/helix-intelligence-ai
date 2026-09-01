from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Dict, Any
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.scrape_job import ScrapeJob
from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
from app.core.config import settings

async def get_dashboard_metrics(db: AsyncSession) -> Dict[str, Any]:
    if settings.USE_MOCKS:
        return {
            "top_performers": [],
            "reach_leaderboard": [],
            "timeline": [],
            "cross_brand": []
        }

    # 1. Top Performers: Creatives sorted by composite score
    top_query = (
        select(Creative, CreativeScore)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .where(CreativeScore.composite.isnot(None))
        .order_by(desc(CreativeScore.composite))
        .limit(10)
    )
    top_result = await db.execute(top_query)
    top_rows = top_result.all()
    
    top_performers = _map_creatives(top_rows)

    # 2. Reach/Activity Leaderboard: Sorted by impressions_est or days_active
    reach_query = (
        select(Creative, CreativeScore)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .order_by(desc(func.coalesce(Creative.impressions_est, 0)), desc(Creative.days_active))
        .limit(10)
    )
    reach_result = await db.execute(reach_query)
    reach_rows = reach_result.all()
    
    reach_leaderboard = _map_creatives(reach_rows)

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
    
    timeline = [{"date": str(row.date), "count": row.creative_count} for row in timeline_rows]

    # 4. Cross-Brand Comparison: Aggregated metrics per brand
    brand_query = (
        select(
            Creative.brand_id,
            func.count(Creative.id).label("active_ads"),
            func.avg(CreativeScore.composite).label("avg_score")
        )
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .group_by(Creative.brand_id)
    )
    brand_result = await db.execute(brand_query)
    brand_rows = brand_result.all()
    
    # Get dominant format per brand (simplification: we do it in Python)
    format_query = (
        select(Creative.brand_id, Creative.format, func.count(Creative.id).label("count"))
        .group_by(Creative.brand_id, Creative.format)
    )
    format_result = await db.execute(format_query)
    format_rows = format_result.all()
    
    format_map = {}
    for r in format_rows:
        brand = r.brand_id
        fmt = r.format
        count = r.count
        if brand not in format_map:
            format_map[brand] = {"format": fmt, "count": count}
        elif count > format_map[brand]["count"]:
            format_map[brand] = {"format": fmt, "count": count}

    cross_brand = []
    for r in brand_rows:
        if not r.brand_id:
            continue
        cross_brand.append({
            "brand_id": r.brand_id,
            "name": r.brand_id.replace("-", " ").title(),
            "active_ads": r.active_ads,
            "avg_score": float(r.avg_score) if r.avg_score else None,
            "dominant_format": format_map.get(r.brand_id, {}).get("format", "unknown")
        })

    return {
        "top_performers": [c.dict() for c in top_performers],
        "reach_leaderboard": [c.dict() for c in reach_leaderboard],
        "timeline": timeline,
        "cross_brand": cross_brand
    }

def _map_creatives(rows):
    items = []
    for c, score in rows:
        items.append(CreativeSchema(
            id=c.id,
            brand_id=c.brand_id,
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
