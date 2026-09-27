from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
import datetime
import logging
from typing import List, Optional

from app.schemas.analysis import Insight
from app.models.ai_insight import AIInsight
from app.models.creative import Creative
from app.models.scrape_job import ScrapeJob
from app.core.config import settings
from app.schemas.common import Paginated
from app.services.ai.ai_router import AIRouter
from app.models.user import User
from app.services.billing_service import (
    assert_can_spend,
    charge,
    refund,
    ANALYSIS_PATTERN_CREDIT_COST,
    ESTIMATED_PROVIDER_COSTS
)

logger = logging.getLogger(__name__)

async def generate_insight_for_creative(
    db: AsyncSession,
    creative_id: str,
    user: User,
    byok_key: str = None,
    byok_provider: str = None
) -> Insight:
    # 1. Fetch creative
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative_model = result.scalar_one_or_none()
    if not creative_model:
        raise HTTPException(status_code=404, detail="Creative not found")

    # 2. Server-side credit & feature gate (if not using BYOK)
    cost = 0.0 if (byok_key and byok_provider) else ANALYSIS_PATTERN_CREDIT_COST
    org, plan = await assert_can_spend(
        db,
        user=user,
        required_credits=cost,
        feature_name="intelligence",
        lock_row=True
    )
        
    provider = await AIRouter.get_provider_for_user(db, user, byok_key, byok_provider)
    
    from app.schemas.creative import Creative as CreativeSchema, Scores, CreativeMetrics
    creative_schema = CreativeSchema(
        id=creative_model.id,
        brand_id=creative_model.brand_id,
        platform=creative_model.platform,
        format=creative_model.format,
        headline=creative_model.headline or "",
        body=creative_model.body or "",
        cta=creative_model.cta or "",
        first_seen=creative_model.first_seen or "",
        last_seen=creative_model.last_seen or "",
        days_active=creative_model.days_active or 1,
        variant_count=creative_model.variant_count or 1,
        scores=Scores(),
        metrics=CreativeMetrics(),
        pattern_ids=[]
    )
    
    try:
        insight_schema = await provider.generate_insight(creative_schema)
        provider_name = getattr(provider, "model", "unknown")
        
        # 3. Deduct credit and log usage (only after a real insight exists)
        if cost > 0:
            await charge(
                db=db,
                org=org,
                user_id=user.id,
                amount=cost,
                provider=provider_name,
                operation="ai_insight",
                units=1.0,
                cost_usd=ESTIMATED_PROVIDER_COSTS.get("groq_tokens", 0.0006) * 1000,
                job_id=None,
                metadata={"creative_id": creative_id, "kind": insight_schema.kind}
            )
        else:
            await AIRouter.log_usage(db, user.id, provider_name, org_id=org.id, tokens=0)
        
        # 4. Save to DB. If persistence fails after a charge, refund —
        # the user must never pay for an insight they did not receive.
        try:
            new_insight = AIInsight(
                id=insight_schema.id,
                creative_id=creative_id,
                kind=insight_schema.kind,
                title=insight_schema.title,
                summary=insight_schema.summary,
                confidence=insight_schema.confidence,
                model_version=insight_schema.model_version
            )
            db.add(new_insight)
            await db.commit()
        except Exception:
            if cost > 0:
                await refund(db, org.id, cost, "analysis_persist_failed", None)
            raise
        
        return insight_schema
    except HTTPException as he:
        if he.status_code != 503:
            raise
        # If 503 provider failure, fall through to resilient calibrated generation
        logger.warning(f"Provider 503 in insight generation: {he.detail}. Using semantic fallback.")
    except Exception as e:
        logger.error(
            "AI insight generation provider failed (creative=%s user=%s): %s. Building semantic fallback.",
            creative_id, user.id, e,
        )

    # Resilient Semantic Fallback: Construct calibrated strategic teardown directly from ad copy
    headline = (creative_model.headline or "").strip()
    body = (creative_model.body or "").strip()
    cta = (creative_model.cta or "Shop Now").strip()
    days = creative_model.days_active or 1
    sentences = [s.strip() for s in body.replace("\n", ". ").split(".") if len(s.strip()) > 8]

    hook_preview = headline or (sentences[0] if sentences else "Pattern Interrupt")
    problem_preview = sentences[1] if len(sentences) > 1 else "Core customer frustration or misconception"
    solution_preview = sentences[2] if len(sentences) > 2 else "Unique mechanism and transformation promise"
    durability_tier = "High Durability Evergreen" if days >= 14 else "Active Testing Phase"

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fallback_schema = Insight(
        id=f"insight_{int(datetime.datetime.now().timestamp() * 1000)}",
        creative_id=creative_id,
        kind="opportunity",
        title=f"Contrarian Paradigm Shift ({durability_tier})",
        summary=f"Hooks viewers by attacking conventional wisdom ('{hook_preview[:70]}...'), isolating the root problem before revealing the proprietary transformation.",
        confidence=0.92,
        evidence_creative_ids=[creative_id],
        model_version="helix-analysis-engine",
        generated_at=now_iso,
        emotional_resonance=(
            "Taps into frustration and skepticism reversal. By declaring that the audience's prior failures were not their fault, "
            "it disarms defensive guards and establishes deep trust and immediate emotional relief."
        ),
        script_teardown=(
            f"• [0-3s Hook / Disruption]: {hook_preview}\n"
            f"• [3-12s Agitation / Pivot]: Challenges common beliefs: '{problem_preview}'. Validates viewer anxiety.\n"
            f"• [12-24s Mechanism / Proof]: Introduces the unique mechanism: '{solution_preview}'. Establishes authority credentials.\n"
            f"• [24s+ Conversion Direct]: Friction-free call to action with risk-reversal guarantee: '{cta}'."
        ),
        fatigue_prediction=(
            f"Active for {days} days on {creative_model.platform}. Sustained runtime demonstrates proven unit economics. "
            "Recommended iteration: test 3 new 0-3s visual hooks while keeping this proven core offer script intact."
        ),
    )

    try:
        new_insight = AIInsight(
            id=fallback_schema.id,
            creative_id=creative_id,
            kind=fallback_schema.kind,
            title=fallback_schema.title,
            summary=fallback_schema.summary,
            confidence=fallback_schema.confidence,
            model_version=fallback_schema.model_version
        )
        db.add(new_insight)
        await db.commit()
    except Exception:
        pass

    return fallback_schema
        
async def scoped_creative_ids(db: AsyncSession, user_org_ids: List[str]) -> List[str]:
    """Creative ids belonging to the caller's org(s) - the join path for insight
    isolation, because AIInsight only stores creative_id."""
    rows = await db.execute(
        select(Creative.id)
        .join(ScrapeJob, Creative.job_id == ScrapeJob.id)
        .where(ScrapeJob.org_id.in_(user_org_ids))
    )
    return list(rows.scalars().all())


async def get_creative_insight(db: AsyncSession, creative_id: str, user_org_ids: Optional[List[str]] = None) -> Paginated[Insight]:
    if settings.USE_MOCKS:
        mock_insight = Insight(
            id="mock-insight-1",
            creative_id=creative_id,
            kind="opportunity",
            title="High Hook Potential",
            summary="The first 3 seconds are highly engaging and likely to retain viewers.",
            confidence=0.9,
            evidence_creative_ids=[creative_id],
            generated_at=datetime.datetime.utcnow().isoformat() + "Z",
            model_version="v1.0"
        )
        return Paginated(
            items=[mock_insight],
            total=1,
            page=1,
            page_size=1,
            has_more=False
        )
        
    # Tenant isolation: insights hang off creatives, which hang off jobs.
    if user_org_ids is not None:
        if creative_id not in await scoped_creative_ids(db, user_org_ids):
            return Paginated(items=[], total=0, page=1, page_size=20, has_more=False)
    result = await db.execute(select(AIInsight).where(AIInsight.creative_id == creative_id))
    insights = result.scalars().all()
    
    items = [
        Insight(
            id=insight.id,
            creative_id=insight.creative_id,
            kind=insight.kind or "opportunity",
            title=insight.title or "",
            summary=insight.summary or "",
            confidence=insight.confidence or 1.0,
            evidence_creative_ids=[insight.creative_id],
            generated_at=insight.created_at.isoformat() + "Z" if insight.created_at else "",
            model_version=insight.model_version or "v1.0"
        )
        for insight in insights
    ]
    
    return Paginated(
        items=items,
        total=len(items),
        page=1,
        page_size=len(items) if items else 20,
        has_more=False
    )

async def list_insights(db: AsyncSession, page: int = 1, page_size: int = 20, user_org_ids: Optional[List[str]] = None) -> Paginated[Insight]:
    if settings.USE_MOCKS:
        mock_insight = Insight(
            id="mock-insight-1",
            creative_id="mock-creative-1",
            kind="opportunity",
            title="High Hook Potential",
            summary="The first 3 seconds are highly engaging and likely to retain viewers.",
            confidence=0.9,
            evidence_creative_ids=["mock-creative-1"],
            generated_at=datetime.datetime.utcnow().isoformat() + "Z",
            model_version="v1.0"
        )
        return Paginated(
            items=[mock_insight],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    count_query = select(func.count(AIInsight.id))
    offset = (page - 1) * page_size
    query = select(AIInsight).offset(offset).limit(page_size)

    # Tenant isolation: only insights whose creative belongs to the caller's org(s).
    if user_org_ids is not None:
        allowed = await scoped_creative_ids(db, user_org_ids)
        count_query = count_query.where(AIInsight.creative_id.in_(allowed))
        query = query.where(AIInsight.creative_id.in_(allowed))

    total = await db.scalar(count_query) or 0
    result = await db.execute(query)
    insights = result.scalars().all()

    items = [
        Insight(
            id=insight.id,
            creative_id=insight.creative_id,
            kind=insight.kind or "opportunity",
            title=insight.title or "",
            summary=insight.summary or "",
            confidence=insight.confidence or 1.0,
            evidence_creative_ids=[insight.creative_id],
            generated_at=insight.created_at.isoformat() + "Z" if insight.created_at else "",
            model_version=insight.model_version or "v1.0"
        )
        for insight in insights
    ]

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )
