from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
from typing import List, Optional

from app.schemas.analysis import Insight
from app.models.ai_insight import AIInsight
from app.models.creative import Creative
from app.models.scrape_job import ScrapeJob
from app.schemas.common import Paginated
from app.services.query_bounds import pagination_bounds

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
