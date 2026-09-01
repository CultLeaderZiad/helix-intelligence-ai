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

# --- Swipe Files / Saved Creatives (Gated by 'swipe_files', 0 credit cost) ---
async def save_creative(
    db: AsyncSession,
    user: "User",
    creative_id: str,
    collection_name: str = "Default",
    tags: Optional[list] = None
) -> dict:
    from app.services.billing_service import check_quota_and_feature
    from app.models.saved_creative import SavedCreative
    from app.models.creative import Creative

    # 1. Check feature flag (0 credits required)
    org, plan = await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)

    # 2. Check creative exists
    creative = (await db.execute(select(Creative).where(Creative.id == creative_id))).scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    # 3. Check already saved
    existing = (await db.execute(
        select(SavedCreative).where(
            SavedCreative.user_id == user.id,
            SavedCreative.creative_id == creative_id
        )
    )).scalar_one_or_none()

    if existing:
        existing.collection_name = collection_name
        if tags is not None:
            existing.tags = tags
        await db.commit()
        return {"success": True, "message": "Saved creative collection updated", "saved_id": existing.id}

    new_saved = SavedCreative(
        user_id=user.id,
        org_id=org.id,
        creative_id=creative_id,
        collection_name=collection_name,
        tags=tags or []
    )
    db.add(new_saved)
    await db.commit()
    await db.refresh(new_saved)
    return {"success": True, "message": "Creative saved to swipe file (0 credits used)", "saved_id": new_saved.id}

async def unsave_creative(db: AsyncSession, user: "User", creative_id: str) -> dict:
    from app.models.saved_creative import SavedCreative
    from sqlalchemy import delete

    result = await db.execute(
        delete(SavedCreative).where(
            SavedCreative.user_id == user.id,
            SavedCreative.creative_id == creative_id
        )
    )
    await db.commit()
    return {"success": True, "message": "Creative removed from swipe file"}

async def list_saved_creatives(
    db: AsyncSession,
    user: "User",
    collection_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Paginated[CreativeSchema]:
    from app.services.billing_service import check_quota_and_feature
    from app.models.saved_creative import SavedCreative
    from app.models.creative import Creative
    from app.models.creative_score import CreativeScore

    # Gated by feature flag
    await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)

    filters = [SavedCreative.user_id == user.id]
    if collection_name:
        filters.append(SavedCreative.collection_name == collection_name)

    count_query = select(func.count(SavedCreative.id)).where(*filters)
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * page_size
    query = (
        select(Creative, CreativeScore, SavedCreative)
        .join(SavedCreative, Creative.id == SavedCreative.creative_id)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .where(*filters)
        .order_by(SavedCreative.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    for c, score, saved in rows:
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

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def create_custom_swipe_reference(db: AsyncSession, user: "User", data: dict) -> dict:
    from app.models.creative import Creative
    from app.models.score import Score
    from app.models.saved_creative import SavedCreative
    from app.services.billing_service import check_quota_and_feature
    import uuid

    org, plan = await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)

    url = data.get("url", "").strip()
    headline = data.get("headline", "").strip() or "Custom Ad Reference"
    body = data.get("body", "").strip() or f"Saved reference link: {url}"
    format_type = data.get("format", "video" if (".mp4" in url or "youtube" in url or "tiktok" in url) else "image")
    platform = data.get("platform", "web")
    collection_name = data.get("collection", "Default")

    new_id = f"custom_{uuid.uuid4().hex[:12]}"
    creative = Creative(
        id=new_id,
        platform=platform,
        format=format_type,
        headline=headline,
        body=body,
        cta=data.get("cta", "Learn More"),
        landing_domain=url[:100] if url else None,
        thumbnail_ratio="1:1" if format_type == "image" else "9:16",
        days_active=1,
        variant_count=1,
        impressions_est=10000
    )
    db.add(creative)

    from app.models.creative_score import CreativeScore
    score = CreativeScore(
        creative_id=new_id,
        hook=None,
        clarity=None,
        retention=None,
        composite=None
    )
    db.add(score)

    saved = SavedCreative(
        user_id=user.id,
        org_id=org.id,
        creative_id=new_id,
        collection_name=collection_name,
        tags=["manual_upload"]
    )
    db.add(saved)

    await db.commit()
    return {"success": True, "message": "Reference added to swipe files", "creative_id": new_id}


