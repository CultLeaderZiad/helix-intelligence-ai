from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.schemas.creative import Creative, Brand
from app.schemas.analysis import Pattern, Insight
from app.schemas.common import Paginated
from app.services import creative_service, analysis_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()
brands_router = APIRouter()
patterns_router = APIRouter()

@router.get("", response_model=Paginated[Creative])
@router.get("/", response_model=Paginated[Creative])
async def get_creatives(
    job_id: Optional[str] = None, 
    brand_id: Optional[str] = None,
    page: int = 1, 
    page_size: int = 20, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await creative_service.list_creatives(db, job_id, brand_id, page, page_size)

@router.get("/saved", response_model=Paginated[Creative])
async def get_saved_creatives(
    collection: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.list_saved_creatives(db, current_user, collection_name=collection, page=page, page_size=page_size)

@router.post("/custom")
async def add_custom_swipe_reference(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.create_custom_swipe_reference(db, current_user, data)

@router.post("/{creative_id}/save")
async def save_creative_to_swipe_file(
    creative_id: str,
    collection: Optional[str] = "Default",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.save_creative(db, current_user, creative_id, collection_name=collection or "Default")

@router.delete("/{creative_id}/save")
async def unsave_creative_from_swipe_file(
    creative_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.unsave_creative(db, current_user, creative_id)

@router.get("/{creative_id}/insights", response_model=Paginated[Insight])
async def get_creative_insights(
    creative_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await analysis_service.get_creative_insight(db, creative_id)

@router.post("/{creative_id}/generate-insights", response_model=Insight)
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

@router.get("/{creative_id}", response_model=Creative)
async def get_creative(
    creative_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.get_creative_by_id(db, creative_id)

@brands_router.get("/", response_model=Paginated[Brand])
async def get_brands(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.list_brands(db, page, page_size)

@patterns_router.get("/", response_model=Paginated[Pattern])
async def get_patterns(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.list_patterns(db, page, page_size)

@patterns_router.post("/generate", response_model=List[Pattern])
async def generate_patterns(
    byok_key: str = None,
    byok_provider: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.generate_patterns_for_recent_creatives(
        db, current_user, byok_key, byok_provider
    )
