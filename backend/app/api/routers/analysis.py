from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.analysis import Insight
from app.schemas.common import Paginated
from app.services import analysis_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()
insights_router = APIRouter()
creatives_insights_router = APIRouter()

@creatives_insights_router.get("/{creative_id}/insights", response_model=Paginated[Insight])
async def get_creative_insights(
    creative_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await analysis_service.get_creative_insight(db, creative_id)

@creatives_insights_router.post("/{creative_id}/generate-insights", response_model=Insight)
async def generate_creative_insights(
    creative_id: str,
    byok_key: str = None,
    byok_provider: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await analysis_service.generate_insight_for_creative(
        db, creative_id, current_user, byok_key, byok_provider
    )


@insights_router.get("/", response_model=Paginated[Insight])
async def list_insights(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await analysis_service.list_insights(db, page, page_size)

