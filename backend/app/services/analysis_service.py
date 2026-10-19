from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
import logging
import uuid
from typing import List, Optional

from app.schemas.analysis import Insight
from app.models.ai_insight import AIInsight
from app.models.creative import Creative
from app.models.scrape_job import ScrapeJob
from app.schemas.common import Paginated
from app.services.query_bounds import pagination_bounds
from app.services.ai.ai_router import AIRouter
from app.models.user import User
from app.services.billing_service import (
    assert_can_spend,
    ANALYSIS_PATTERN_CREDIT_COST,
)

logger = logging.getLogger(__name__)


async def _release_insight_hold(db, reservation, org) -> None:
    if reservation is None:
        return
    from app.services.billing_service import release_reservation
    try:
        released = await release_reservation(db, reservation.id, "insight_provider_failed")
    except Exception:
        released = False
    if not released and getattr(reservation, "status", None) != "refunded":
        if org is not None and getattr(org, "credit_balance", None) is not None:
            org.credit_balance = float(org.credit_balance) + float(reservation.amount)

async def generate_insight_for_creative(
    db: AsyncSession,
    creative_id: str,
    user: User,
    byok_key: str = None,
    byok_provider: str = None,
    user_org_ids: Optional[List[str]] = None
) -> Insight:
    # 1. Fetch creative
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative_model = result.scalar_one_or_none()
    if not creative_model:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Tenant isolation: ensure creative belongs to caller's org(s) (F06)
    if user_org_ids is not None:
        job_org = (await db.execute(
            select(ScrapeJob.org_id).where(ScrapeJob.id == creative_model.job_id)
        )).scalar_one_or_none()
        if job_org not in user_org_ids:
            raise HTTPException(status_code=404, detail="Creative not found")

    # 2. Server-side credit & feature gate (if not using BYOK).
    # The pre-check does not hold the org row. reserve_credits commits the hold
    # before the provider call so the lock is gone during network I/O.
    cost = 0.0 if (byok_key and byok_provider) else ANALYSIS_PATTERN_CREDIT_COST
    org, plan = await assert_can_spend(
        db,
        user=user,
        required_credits=cost,
        feature_name="intelligence",
        lock_row=False
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
    reservation = None
    if cost > 0:
        from app.services.billing_service import reserve_credits
        reservation = await reserve_credits(
            db,
            org=org,
            user_id=user.id,
            amount=cost,
            operation="ai_insight",
            idempotency_key=f"ai_insight:{creative_id}:{uuid.uuid4().hex}",
            metadata={"creative_id": creative_id},
            provider="pending",
        )

    try:
        insight_schema = await provider.generate_insight(creative_schema)
        provider_name = getattr(provider, "model", None) or "unknown"
        if not isinstance(provider_name, str):
            provider_name = "unknown"
        usage = getattr(provider, "last_usage", None)
        from app.services.ai.call_policy import ChatResult, usage_metadata
        if not isinstance(usage, ChatResult):
            usage = None
        from app.services.ai.prompts import PROMPT_INSIGHT
        meta = usage_metadata(usage, prompt_version=PROMPT_INSIGHT)
        meta["creative_id"] = creative_id
        meta["kind"] = insight_schema.kind

        # 4. Persist the validated insight and settle the hold in one commit.
        try:
            reasons_payload = {
                "emotional_resonance": getattr(insight_schema, "emotional_resonance", None),
                "script_teardown": getattr(insight_schema, "script_teardown", None),
                "fatigue_prediction": getattr(insight_schema, "fatigue_prediction", None),
                "key_elements": getattr(insight_schema, "key_elements", None),
                "recommendations": getattr(insight_schema, "recommendations", None),
                "usage": meta,
            }
            new_insight = AIInsight(
                id=insight_schema.id,
                creative_id=creative_id,
                kind=insight_schema.kind,
                title=insight_schema.title,
                summary=insight_schema.summary,
                reasons=reasons_payload,
                confidence=insight_schema.confidence,
                evidence_creative_ids=insight_schema.evidence_creative_ids or [creative_id],
                model_version=insight_schema.model_version
            )
            db.add(new_insight)
            if reservation is not None:
                from app.services.billing_service import settle_reservation
                await settle_reservation(
                    db,
                    reservation.id,
                    provider=getattr(usage, "provider", None) or provider_name,
                    model=getattr(usage, "model", None) or provider_name,
                    tokens=getattr(usage, "total_tokens", None),
                    cost_usd=getattr(usage, "cost_usd", None),
                    latency_ms=getattr(usage, "latency_ms", None),
                    metadata=meta,
                    commit=False,
                )
            else:
                await AIRouter.log_usage(
                    db,
                    user.id,
                    provider_name,
                    org_id=org.id,
                    tokens=int(getattr(usage, "total_tokens", 0) or 0),
                )
            await db.commit()
        except Exception:
            await db.rollback()
            if reservation is not None:
                from app.services.billing_service import release_reservation
                await release_reservation(db, reservation.id, "analysis_persist_failed")
            raise

        return insight_schema
    except HTTPException:
        await _release_insight_hold(db, reservation, org)
        raise
    except Exception as e:
        await _release_insight_hold(db, reservation, org)
        logger.error(
            "AI insight generation provider failed (creative=%s user=%s): %s",
            creative_id, user.id, e,
        )
        raise HTTPException(
            status_code=503,
            detail=f"AI insight generation service is temporarily unavailable: {str(e)}"
        )
        
def scoped_creative_ids(user_org_ids: List[str]):
    """Keep the ownership join in SQL, never load a tenant's full ID set."""
    return (
        select(Creative.id)
        .join(ScrapeJob, Creative.job_id == ScrapeJob.id)
        .where(ScrapeJob.org_id.in_(user_org_ids))
    )


async def get_creative_insight(
    db: AsyncSession, creative_id: str, user_org_ids: Optional[List[str]] = None,
    page: int = 1, page_size: int = 20,
) -> Paginated[Insight]:
    offset, page_size = pagination_bounds(page, page_size)
    filters = [AIInsight.creative_id == creative_id]
    # Tenant isolation: insights hang off creatives, which hang off jobs.
    if user_org_ids is not None:
        filters.append(AIInsight.creative_id.in_(scoped_creative_ids(user_org_ids)))
    total = await db.scalar(select(func.count(AIInsight.id)).where(*filters)) or 0
    result = await db.execute(
        select(AIInsight).where(*filters).order_by(AIInsight.id).offset(offset).limit(page_size)
    )
    insights = result.scalars().all()
    
    items = []
    for insight in insights:
        reasons = insight.reasons if isinstance(insight.reasons, dict) else {}
        items.append(
            Insight(
                id=insight.id,
                creative_id=insight.creative_id,
                kind=insight.kind or "opportunity",
                title=insight.title or "",
                summary=insight.summary or "",
                confidence=insight.confidence or 1.0,
                evidence_creative_ids=insight.evidence_creative_ids or [insight.creative_id],
                generated_at=insight.generated_at or (insight.created_at.isoformat() + "Z" if getattr(insight, "created_at", None) else ""),
                model_version=insight.model_version or "v1.0",
                emotional_resonance=reasons.get("emotional_resonance"),
                script_teardown=reasons.get("script_teardown"),
                fatigue_prediction=reasons.get("fatigue_prediction"),
                key_elements=reasons.get("key_elements"),
                recommendations=reasons.get("recommendations"),
            )
        )
    
    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def list_insights(db: AsyncSession, page: int = 1, page_size: int = 20, user_org_ids: Optional[List[str]] = None) -> Paginated[Insight]:
    offset, page_size = pagination_bounds(page, page_size)
    count_query = select(func.count(AIInsight.id))
    query = select(AIInsight).order_by(AIInsight.id).offset(offset).limit(page_size)

    # Tenant isolation: only insights whose creative belongs to the caller's org(s).
    if user_org_ids is not None:
        allowed = scoped_creative_ids(user_org_ids)
        count_query = count_query.where(AIInsight.creative_id.in_(allowed))
        query = query.where(AIInsight.creative_id.in_(allowed))

    total = await db.scalar(count_query) or 0
    result = await db.execute(query)
    insights = result.scalars().all()

    items = []
    for insight in insights:
        reasons = insight.reasons if isinstance(insight.reasons, dict) else {}
        items.append(
            Insight(
                id=insight.id,
                creative_id=insight.creative_id,
                kind=insight.kind or "opportunity",
                title=insight.title or "",
                summary=insight.summary or "",
                confidence=insight.confidence or 1.0,
                evidence_creative_ids=insight.evidence_creative_ids or [insight.creative_id],
                generated_at=insight.generated_at or (insight.created_at.isoformat() + "Z" if getattr(insight, "created_at", None) else ""),
                model_version=insight.model_version or "v1.0",
                emotional_resonance=reasons.get("emotional_resonance"),
                script_teardown=reasons.get("script_teardown"),
                fatigue_prediction=reasons.get("fatigue_prediction"),
                key_elements=reasons.get("key_elements"),
                recommendations=reasons.get("recommendations"),
            )
        )

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )
