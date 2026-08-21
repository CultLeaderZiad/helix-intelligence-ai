from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
from app.schemas.common import Paginated
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.core.config import settings
import datetime

from typing import Optional
from app.schemas.creative import Brand as BrandSchema
from app.schemas.analysis import Pattern as PatternSchema
from app.models.pattern import Pattern
from fastapi import HTTPException

async def list_creatives(
    db: AsyncSession, 
    job_id: Optional[str] = None, 
    brand_id: Optional[str] = None, 
    page: int = 1, 
    page_size: int = 20
) -> Paginated[CreativeSchema]:
    if settings.USE_MOCKS:
        mock_creative = CreativeSchema(
            id="mock-creative-1",
            brand_id="mock-brand",
            platform="meta",
            format="video",
            headline="Try this now!",
            body="This is an amazing product.",
            cta="Learn More",
            first_seen=datetime.datetime.utcnow().isoformat() + "Z",
            last_seen=datetime.datetime.utcnow().isoformat() + "Z",
            days_active=5,
            variant_count=3,
            scores=Scores(hook=85.0, clarity=90.0, retention=80.0, composite=85.0),
            metrics=CreativeMetrics(impressions_est=10000, spend_band="high", engagement_rate=0.05, ctr_est=0.02),
            pattern_ids=["mock-pattern-1"]
        )
        
        return Paginated(
            items=[mock_creative],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    # Build filters dynamically
    filters = []
    if job_id:
        filters.append(Creative.job_id == job_id)
    if brand_id:
        filters.append(Creative.brand_id == brand_id)

    # Count total
    count_query = select(func.count(Creative.id))
    if filters:
        count_query = count_query.where(*filters)
    total = await db.scalar(count_query) or 0

    # Fetch paginated
    offset = (page - 1) * page_size
    query = select(Creative, CreativeScore).outerjoin(
        CreativeScore, Creative.id == CreativeScore.creative_id
    )
    if filters:
        query = query.where(*filters)
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()

    items = []
    for c, score in rows:
        items.append(CreativeSchema(
            id=c.id,
            brand_id=c.brand_id,
            platform=c.platform,
            format=c.format,
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
                spend_band=c.spend_band,
                engagement_rate=c.engagement_rate,
                ctr_est=c.ctr_est
            ),
            pattern_ids=[]  # Omitted for simplicity unless creative_patterns mapping exists
        ))

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def get_creative_by_id(db: AsyncSession, creative_id: str) -> CreativeSchema:
    if settings.USE_MOCKS:
        return CreativeSchema(
            id=creative_id,
            brand_id="mock-brand",
            platform="meta",
            format="video",
            headline="Mock Headline",
            body="Mock Body",
            cta="Learn More",
            first_seen=datetime.datetime.utcnow().isoformat() + "Z",
            last_seen=datetime.datetime.utcnow().isoformat() + "Z",
            days_active=5,
            variant_count=3,
            scores=Scores(hook=85.0, clarity=90.0, retention=80.0, composite=85.0),
            metrics=CreativeMetrics(impressions_est=10000, spend_band="high", engagement_rate=0.05, ctr_est=0.02),
            pattern_ids=["mock-pattern-1"]
        )

    query = select(Creative, CreativeScore).outerjoin(
        CreativeScore, Creative.id == CreativeScore.creative_id
    ).where(Creative.id == creative_id)
    
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Creative not found")
        
    c, score = row
    return CreativeSchema(
        id=c.id,
        brand_id=c.brand_id,
        platform=c.platform,
        format=c.format,
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
            spend_band=c.spend_band,
            engagement_rate=c.engagement_rate,
            ctr_est=c.ctr_est
        ),
        pattern_ids=[]
    )

async def list_brands(db: AsyncSession, page: int = 1, page_size: int = 20) -> Paginated[BrandSchema]:
    if settings.USE_MOCKS:
        mock_brand = BrandSchema(
            id="mock-brand",
            name="Mock Brand",
            domain="mockbrand.com",
            category="Software",
            ad_count=12,
            first_seen=datetime.datetime.utcnow().isoformat() + "Z"
        )
        return Paginated(
            items=[mock_brand],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    # Since we don't have a separate Brand table, we can generate unique brands from creatives
    # Grouping creatives by brand_id
    query = select(Creative.brand_id, func.count(Creative.id).label("ad_count")).group_by(Creative.brand_id)
    result = await db.execute(query)
    rows = result.all()
    
    total = len(rows)
    offset = (page - 1) * page_size
    paginated_rows = rows[offset:offset+page_size]
    
    items = []
    for brand_id, ad_count in paginated_rows:
        items.append(BrandSchema(
            id=brand_id,
            name=brand_id.replace("-", " ").title(),
            domain=f"{brand_id}.com",
            category="Other",
            ad_count=ad_count,
            first_seen=datetime.datetime.utcnow().isoformat() + "Z"
        ))
        
    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def list_patterns(db: AsyncSession, page: int = 1, page_size: int = 20) -> Paginated[PatternSchema]:
    if settings.USE_MOCKS:
        mock_pattern = PatternSchema(
            id="mock-pattern-1",
            label="Fast Paced Cuts",
            family="visual",
            prevalence=0.45,
            lift_index=1.25
        )
        return Paginated(
            items=[mock_pattern],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    count_query = select(func.count(Pattern.id))
    total = await db.scalar(count_query) or 0
    
    offset = (page - 1) * page_size
    query = select(Pattern).offset(offset).limit(page_size)
    result = await db.execute(query)
    patterns = result.scalars().all()
    
    items = [
        PatternSchema(
            id=p.id,
            label=p.label,
            family=p.family,
            prevalence=p.prevalence,
            lift_index=p.lift_index
        )
        for p in patterns
    ]
    
    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

from app.services.ai.ai_router import AIRouter
from app.models.user import User
from typing import List

async def generate_patterns_for_recent_creatives(db: AsyncSession, user: User, job_id: str, byok_key: str = None, byok_provider: str = None) -> List[PatternSchema]:
    # Fetch recent creatives (e.g., last 10)
    query = select(Creative).order_by(Creative.first_seen.desc()).limit(10)
    result = await db.execute(query)
    creatives_models = result.scalars().all()
    
    if not creatives_models:
        raise HTTPException(status_code=400, detail="No creatives available for pattern extraction")
        
    provider = await AIRouter.get_provider_for_user(db, user, byok_key, byok_provider)
    
    # Map to schema
    from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
    creative_schemas = []
    for c in creatives_models:
        creative_schemas.append(CreativeSchema(
            id=c.id,
            brand_id=c.brand_id,
            platform=c.platform,
            format=c.format,
            headline=c.headline or "",
            body=c.body or "",
            cta=c.cta or "",
            first_seen=c.first_seen or "",
            last_seen=c.last_seen or "",
            days_active=c.days_active or 1,
            variant_count=c.variant_count or 1,
            scores=Scores(),
            metrics=CreativeMetrics(),
            pattern_ids=[]
        ))
        
    try:
        patterns = await provider.generate_patterns(creative_schemas)
        
        # Log usage
        await AIRouter.log_usage(db, user.id, getattr(provider, "model", "unknown"), tokens=0)
        
        # Save patterns to DB
        for p_schema in patterns:
            new_pattern = Pattern(
                id=p_schema.id,
                label=p_schema.label,
                family=p_schema.family,
                prevalence=p_schema.prevalence,
                lift_index=p_schema.lift_index,
                job_id=job_id
            )
            db.add(new_pattern)
        
        await db.commit()
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
