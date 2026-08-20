from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.schemas.analysis import Insight
from app.models.ai_insight import AIInsight
from app.core.config import settings
import datetime

from app.schemas.common import Paginated
from sqlalchemy import func

async def get_creative_insight(db: AsyncSession, creative_id: str) -> Paginated[Insight]:
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

async def list_insights(db: AsyncSession, page: int = 1, page_size: int = 20) -> Paginated[Insight]:
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
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * page_size
    query = select(AIInsight).offset(offset).limit(page_size)
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


