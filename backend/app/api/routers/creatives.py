from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.schemas.creative import Creative, Brand
from app.schemas.analysis import Pattern
from app.schemas.common import Paginated
from app.services import creative_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()
brands_router = APIRouter()
patterns_router = APIRouter()

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

from typing import List

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


