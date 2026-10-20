from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
from app.schemas.common import Paginated
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.scrape_job import ScrapeJob
from app.services.query_bounds import pagination_bounds
import datetime

from typing import List, Optional
from app.schemas.creative import Brand as BrandSchema
from app.schemas.analysis import Pattern as PatternSchema
from app.models.pattern import Pattern
from fastapi import HTTPException
import logging
from app.core.observability import log_event

logger = logging.getLogger(__name__)

async def list_creatives(
    db: AsyncSession,
    job_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user_org_ids: Optional[List[str]] = None
) -> Paginated[CreativeSchema]:
    offset, page_size = pagination_bounds(page, page_size)
    # Build filters dynamically
    filters = []
    if job_id:
        filters.append(Creative.job_id == job_id)
    if brand_id:
        filters.append(Creative.brand_id == brand_id)
    # Tenant isolation: creatives carry no org_id, so scope through their job.
    if user_org_ids is not None:
        scoped_job_ids = select(ScrapeJob.id).where(ScrapeJob.org_id.in_(user_org_ids))
        filters.append(Creative.job_id.in_(scoped_job_ids))

    # Count total
    count_query = select(func.count(Creative.id))
    if filters:
        count_query = count_query.where(*filters)
    total = await db.scalar(count_query) or 0

    # Fetch paginated
    query = select(Creative, CreativeScore).outerjoin(
        CreativeScore, Creative.id == CreativeScore.creative_id
    )
    if filters:
        query = query.where(*filters)
    query = query.order_by(Creative.id).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()

    items = []
    for c, score in rows:
        items.append(CreativeSchema(
            id=c.id,
            brand_id=c.brand_id,
            brand_name=getattr(c, "brand_name", None),
            platform=c.platform,
            format=c.format,
            source_type=getattr(c, "data_source", "ad") or "ad",
            headline=c.headline or "",
            body=c.body or "",
            cta=c.cta or "",
            landing_domain=c.landing_domain,
            media_url=getattr(c, "media_url", None),
            thumbnail_url=getattr(c, "thumbnail_url", None),
            thumbnail_ratio=c.thumbnail_ratio,
            duration_seconds=c.duration_seconds,
            first_seen=c.first_seen or "",
            last_seen=c.last_seen or "",
            days_active=c.days_active,
            variant_count=c.variant_count or 1,
            source_ad_id=getattr(c, "source_ad_id", None),
            permalink=getattr(c, "permalink", None),
            fetched_at=c.fetched_at.isoformat() if getattr(c, "fetched_at", None) else None,
            scores=Scores(
                hook=score.hook if score else None,
                clarity=score.clarity if score else None,
                retention=score.retention if score else None,
                composite=score.composite if score else None,
                basis=getattr(c, "score_basis", None) or "heuristic",
                scale=getattr(c, "score_scale", None) or "0-10",
                version=getattr(c, "heuristic_version", None),
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

async def get_creative_by_id(
    db: AsyncSession, creative_id: str, user_org_ids: Optional[List[str]] = None
) -> CreativeSchema:
    query = select(Creative, CreativeScore).outerjoin(
        CreativeScore, Creative.id == CreativeScore.creative_id
    ).where(Creative.id == creative_id)
    
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Tenant isolation: resolve the owning job's org; 404 on mismatch.
    if user_org_ids is not None:
        job_org = (await db.execute(
            select(ScrapeJob.org_id).where(ScrapeJob.id == row[0].job_id)
        )).scalar_one_or_none()
        if job_org not in user_org_ids:
            raise HTTPException(status_code=404, detail="Creative not found")
        
    c, score = row
    return CreativeSchema(
        id=c.id,
        brand_id=c.brand_id,
        brand_name=getattr(c, "brand_name", None),
        platform=c.platform,
        format=c.format,
        source_type=getattr(c, "data_source", "ad") or "ad",
        headline=c.headline or "",
        body=c.body or "",
        cta=c.cta or "",
        landing_domain=c.landing_domain,
        media_url=getattr(c, "media_url", None),
        thumbnail_url=getattr(c, "thumbnail_url", None),
        thumbnail_ratio=c.thumbnail_ratio,
        duration_seconds=c.duration_seconds,
        first_seen=c.first_seen or "",
        last_seen=c.last_seen or "",
        days_active=c.days_active,
        variant_count=c.variant_count or 1,
        source_ad_id=getattr(c, "source_ad_id", None),
        permalink=getattr(c, "permalink", None),
        fetched_at=c.fetched_at.isoformat() if getattr(c, "fetched_at", None) else None,
        scores=Scores(
            hook=score.hook if score else None,
            clarity=score.clarity if score else None,
            retention=score.retention if score else None,
            composite=score.composite if score else None,
            basis=getattr(c, "score_basis", None) or "heuristic",
            scale=getattr(c, "score_scale", None) or "0-10",
            version=getattr(c, "heuristic_version", None),
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

async def list_brands(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    user_org_ids: Optional[List[str]] = None
) -> Paginated[BrandSchema]:
    offset, page_size = pagination_bounds(page, page_size)
    # Since we don't have a separate Brand table, generate unique brands from creatives
    query = select(
        Creative.brand_id,
        func.max(Creative.brand_name).label("brand_name"),
        func.count(Creative.id).label("ad_count")
    )
    if user_org_ids is not None:
        scoped_jobs = select(ScrapeJob.id).where(ScrapeJob.org_id.in_(user_org_ids))
        query = query.where(Creative.job_id.in_(scoped_jobs))

    query = query.group_by(Creative.brand_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    result = await db.execute(query.order_by(Creative.brand_id).offset(offset).limit(page_size))
    paginated_rows = result.all()
    
    items = []
    for brand_id, brand_name, ad_count in paginated_rows:
        display_name = (brand_name or "").strip() or brand_id.replace("-", " ").title()
        items.append(BrandSchema(
            id=brand_id,
            name=display_name,
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

async def list_patterns(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    user_org_ids: Optional[List[str]] = None
) -> Paginated[PatternSchema]:
    offset, page_size = pagination_bounds(page, page_size)
    # Unowned null-job patterns are not readable by any tenant.
    # Pattern.job_id.is_not(None) stays as containment. Ownership is the org id.
    filters = [Pattern.job_id.is_not(None), Pattern.org_id.is_not(None)]
    if user_org_ids is not None:
        scoped_jobs = select(ScrapeJob.id).where(ScrapeJob.org_id.in_(user_org_ids))
        filters.append(Pattern.org_id.in_(user_org_ids))
        filters.append(Pattern.job_id.in_(scoped_jobs))

    count_query = select(func.count(Pattern.id))
    if filters:
        count_query = count_query.where(*filters)
    total = await db.scalar(count_query) or 0
    
    query = select(Pattern)
    if filters:
        query = query.where(*filters)
    query = query.order_by(Pattern.id).offset(offset).limit(page_size)
    result = await db.execute(query)
    patterns = result.scalars().all()
    
    items = [
        PatternSchema(
            id=p.id,
            label=p.label,
            family=p.family,
            prevalence=p.prevalence,
            lift_index=None,
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

async def generate_patterns_for_recent_creatives(
    db: AsyncSession,
    user: User,
    job_id: Optional[str] = None,
    byok_key: Optional[str] = None,
    byok_provider: Optional[str] = None,
    user_org_ids: Optional[List[str]] = None
) -> List[PatternSchema]:
    # 1. Scope and fetch creatives (F53)
    if job_id:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
        if not job or (user_org_ids is not None and job.org_id not in user_org_ids):
            raise HTTPException(status_code=404, detail="Job not found")
        query = select(Creative).where(Creative.job_id == job_id).limit(10)
    else:
        query = select(Creative)
        if user_org_ids is not None:
            scoped_jobs = select(ScrapeJob.id).where(ScrapeJob.org_id.in_(user_org_ids))
            query = query.where(Creative.job_id.in_(scoped_jobs))
        query = query.order_by(Creative.first_seen.desc()).limit(10)

    result = await db.execute(query)
    creatives_models = result.scalars().all()
    
    if not creatives_models:
        raise HTTPException(
            status_code=400,
            detail="No creatives available for pattern extraction in your workspace. Please run a discovery search first."
        )

    # 2. Server-side credit & feature gate (F53)
    from app.services.billing_service import assert_can_spend, ANALYSIS_PATTERN_CREDIT_COST
    cost = 0.0 if (byok_key and byok_provider) else ANALYSIS_PATTERN_CREDIT_COST
    org, plan = await assert_can_spend(
        db,
        user=user,
        required_credits=cost,
        feature_name="intelligence",
        lock_row=False
    )
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
    reservation = None
    if cost > 0:
        import uuid as _uuid
        from app.services.billing_service import reserve_credits
        reservation = await reserve_credits(
            db,
            org=org,
            user_id=user.id,
            amount=cost,
            operation="pattern_synthesis",
            job_id=job_id,
            idempotency_key=f"pattern_synthesis:{job_id or 'recent'}:{_uuid.uuid4().hex}",
            metadata={"job_id": job_id},
        )

    try:
        patterns = await provider.generate_patterns(creative_schemas)
        usage = getattr(provider, "last_usage", None)
        provider_name = getattr(usage, "model", None) or getattr(provider, "model", "unknown")

        # The lift column is not nullable. 0 is stored and never returned as a measurement.
        if job_id and getattr(job, "org_id", None):
            for p_schema in patterns:
                new_pattern = Pattern(
                    id=p_schema.id,
                    label=p_schema.label,
                    family=p_schema.family,
                    prevalence=p_schema.prevalence,
                    lift_index=None,
                    job_id=job_id,
                    org_id=job.org_id,
                )
                db.add(new_pattern)
        if reservation is not None:
            from app.services.ai.call_policy import usage_metadata
            from app.services.ai.prompts import PROMPT_PATTERNS
            from app.services.billing_service import settle_reservation
            await settle_reservation(
                db,
                reservation.id,
                provider=getattr(usage, "provider", None) or provider_name,
                model=provider_name,
                tokens=getattr(usage, "total_tokens", None),
                cost_usd=getattr(usage, "cost_usd", None),
                latency_ms=getattr(usage, "latency_ms", None),
                metadata=usage_metadata(usage, prompt_version=PROMPT_PATTERNS),
                commit=False,
            )
        await db.commit()
        return patterns
    except HTTPException:
        if reservation is not None:
            from app.services.billing_service import release_reservation
            await release_reservation(db, reservation.id, "pattern_provider_failed")
        raise
    except Exception as e:
        if reservation is not None:
            from app.services.billing_service import release_reservation
            await release_reservation(db, reservation.id, "pattern_provider_failed")
        log_event(logger, "ai_pattern_extraction_failed", error=e, job_id=job_id, actor_id=user.id, tenant_id=org.id)
        try:
            await AIRouter.log_failure(
                db,
                user_id=user.id,
                provider_name=getattr(provider, "model", "unknown"),
                operation="pattern_synthesis",
                org_id=org.id,
                error="pattern_provider_failed",
            )
        except Exception as exc:
            log_event(logger, "ai_pattern_failure_record_failed", error=exc, job_id=job_id, actor_id=user.id, tenant_id=org.id)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "analysis_unavailable",
                "message": "Pattern extraction is temporarily unavailable — the AI provider could not be reached. No credits were charged. Please try again shortly.",
            },
        )

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

    # Tenant isolation: ensure creative belongs to caller's org(s) (F03)
    from app.core.tenancy import get_user_org_ids
    user_org_ids = await get_user_org_ids(db, user)
    if user_org_ids is not None:
        job_org = (await db.execute(
            select(ScrapeJob.org_id).where(ScrapeJob.id == creative.job_id)
        )).scalar_one_or_none()
        if job_org not in user_org_ids:
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
    log_event(logger, "creative_saved", actor_id=user.id, tenant_id=org.id, level=logging.INFO)
    return {"success": True, "message": "Creative saved to swipe file (0 credits used)", "saved_id": new_saved.id}

async def unsave_creative(db: AsyncSession, user: "User", creative_id: str) -> dict:
    from app.models.saved_creative import SavedCreative
    from sqlalchemy import delete

    await db.execute(
        delete(SavedCreative).where(
            SavedCreative.user_id == user.id,
            SavedCreative.creative_id == creative_id
        )
    )
    await db.commit()
    log_event(logger, "creative_unsaved", actor_id=user.id, level=logging.INFO)
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

    offset, page_size = pagination_bounds(page, page_size)
    # Gated by feature flag
    await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)

    filters = [SavedCreative.user_id == user.id]
    if collection_name:
        filters.append(SavedCreative.collection_name == collection_name)

    count_query = select(func.count(SavedCreative.id)).where(*filters)
    total = await db.scalar(count_query) or 0

    query = (
        select(Creative, CreativeScore, SavedCreative)
        .join(SavedCreative, Creative.id == SavedCreative.creative_id)
        .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
        .where(*filters)
        .order_by(SavedCreative.created_at.desc(), SavedCreative.id)
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
            brand_name=getattr(c, "brand_name", None),
            platform=c.platform,
            format=c.format,
            source_type=getattr(c, "data_source", "ad") or "ad",
            headline=c.headline or "",
            body=c.body or "",
            cta=c.cta or "",
            landing_domain=c.landing_domain,
            media_url=getattr(c, "media_url", None),
            thumbnail_url=getattr(c, "thumbnail_url", None),
            thumbnail_ratio=c.thumbnail_ratio,
            duration_seconds=c.duration_seconds,
            first_seen=c.first_seen or "",
            last_seen=c.last_seen or "",
            days_active=c.days_active,
            variant_count=c.variant_count or 1,
            source_ad_id=getattr(c, "source_ad_id", None),
            permalink=getattr(c, "permalink", None),
            fetched_at=c.fetched_at.isoformat() if getattr(c, "fetched_at", None) else None,
            scores=Scores(
                hook=score.hook if score else None,
                clarity=score.clarity if score else None,
                retention=score.retention if score else None,
                composite=score.composite if score else None,
                basis=getattr(c, "score_basis", None) or "heuristic",
                scale=getattr(c, "score_scale", None) or "0-10",
                version=getattr(c, "heuristic_version", None),
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
    from app.models.scrape_job import ScrapeJob
    from app.models.saved_creative import SavedCreative
    from app.services.billing_service import check_quota_and_feature
    import uuid

    org, plan = await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)

    url = data.get("url", "").strip()
    headline = data.get("headline", "").strip() or "Custom Ad Reference"
    body = data.get("body", "").strip() or (f"Saved reference link: {url}" if url else "Custom reference")
    format_type = data.get("format", "video" if (".mp4" in url or "youtube" in url or "tiktok" in url) else "image")
    platform = data.get("platform", "web")
    collection_name = data.get("collection", "Default")

    # Ensure parent ScrapeJob exists for org tenancy & relational integrity (F33)
    custom_job_id = f"custom_job_{org.id}"
    job_exists = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == custom_job_id))).scalar_one_or_none()
    if not job_exists:
        job = ScrapeJob(
            id=custom_job_id,
            org_id=org.id,
            query="Custom Swipe Files",
            status="succeeded",
            record_count=1,
            progress=1.0,
            stage="complete"
        )
        db.add(job)
        await db.flush()

    new_id = f"custom_{uuid.uuid4().hex[:12]}"
    brand_id = f"custom_brand_{uuid.uuid4().hex[:8]}"
    creative = Creative(
        id=new_id,
        job_id=custom_job_id,
        brand_id=brand_id,
        brand_name=headline[:50],
        platform=platform,
        format=format_type,
        headline=headline,
        body=body,
        cta=data.get("cta", "Learn More"),
        landing_domain=url[:100] if url else None,
        thumbnail_ratio="1:1" if format_type == "image" else "9:16",
        days_active=1,
        variant_count=1,
        impressions_est=None,
        is_estimated=False,
        data_source="manual_upload"
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
    log_event(logger, "creative_reference_created", actor_id=user.id, tenant_id=org.id, level=logging.INFO)
    return {"success": True, "message": "Reference added to swipe files", "creative_id": new_id}


def _translation_unavailable(target_lang: str, message: str) -> dict:
    return {
        "status": "unavailable",
        "target_lang": target_lang,
        "detected_lang": None,
        "translated_text": None,
        "breakdown": None,
        "model": None,
        "prompt_version": None,
        "charged": False,
        "error": message,
    }


async def translate_ad_copy(
    text: str,
    target_lang: str = "en",
    breakdown: bool = True,
    db=None,
    user=None,
) -> dict:
    """Translate ad copy with a real provider. Failure returns unavailable and does not charge."""
    del breakdown
    clean_text = (text or "").strip()
    if not clean_text:
        return _translation_unavailable(target_lang, "No copy was provided.")

    lang_map = {"en": "English", "es": "Spanish", "zh": "Chinese", "nl": "Dutch", "ar": "Arabic"}
    target_name = lang_map.get((target_lang or "en").lower(), target_lang or "English")
    reservation = None
    org = None
    if user is not None and db is not None:
        from app.services.billing_service import assert_can_spend, AI_CHAT_CREDIT_COST, reserve_credits
        org, _plan = await assert_can_spend(
            db, user=user, required_credits=AI_CHAT_CREDIT_COST, feature_name="intelligence", lock_row=False
        )
        import uuid as _uuid
        reservation = await reserve_credits(
            db,
            org=org,
            user_id=user.id,
            amount=AI_CHAT_CREDIT_COST,
            operation="copy_translation",
            idempotency_key=f"copy_translation:{_uuid.uuid4().hex}",
            metadata={"target_lang": target_lang},
        )

    from app.core.config import settings as _settings
    from app.core.credentials import env_secret
    from app.services.ai.call_policy import complete_chat
    from app.services.ai.prompts import PROMPT_TRANSLATION, translation_messages
    from app.services.ai.structured import parse_translation
    import json

    api_key = env_secret("GROQ_API_KEY", fallback=_settings.GROQ_API_KEY)
    if not api_key:
        if reservation is not None:
            from app.services.billing_service import release_reservation
            await release_reservation(db, reservation.id, "translation_unavailable")
        return _translation_unavailable(target_lang, "Translation is unavailable because no model provider is configured.")

    try:
        result = await complete_chat(
            provider_name="groq",
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=api_key,
            model=getattr(_settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile",
            fallback_models=["llama-3.1-8b-instant"],
            messages=translation_messages(clean_text, target_name),
            allowed_hosts={"api.groq.com"},
            response_format={"type": "json_object"},
        )
        parsed = parse_translation(json.loads(result.text), target_lang=target_lang)
    except Exception as exc:
        if reservation is not None:
            from app.services.billing_service import release_reservation
            await release_reservation(db, reservation.id, "translation_unavailable")
        log_event(logger, "copy_translation_failed", error=exc, actor_id=getattr(user, "id", None), tenant_id=getattr(org, "id", None))
        return _translation_unavailable(target_lang, "Translation is temporarily unavailable. No credits were charged.")

    parsed["model"] = result.model
    parsed["prompt_version"] = PROMPT_TRANSLATION
    parsed["provider"] = result.provider
    parsed["charged"] = reservation is not None
    if reservation is not None:
        from app.services.ai.call_policy import usage_metadata
        from app.services.billing_service import settle_reservation
        await settle_reservation(
            db,
            reservation.id,
            provider=result.provider,
            model=result.model,
            tokens=result.total_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            metadata=usage_metadata(result, prompt_version=PROMPT_TRANSLATION),
        )
    return parsed


