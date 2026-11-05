from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.schemas.creative import Creative
from app.schemas.common import Paginated
from app.services import creative_service
from app.core.deps import get_db, get_current_user, require_feature
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_feature("intelligence"))])

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
    from app.core.tenancy import get_user_org_ids
    scope = await get_user_org_ids(db, current_user)
    return await creative_service.list_creatives(db, job_id, brand_id, page, page_size, user_org_ids=scope)

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


@router.get("/{creative_id}", response_model=Creative)
async def get_creative(
    creative_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.core.tenancy import get_user_org_ids
    scope = await get_user_org_ids(db, current_user)
    return await creative_service.get_creative_by_id(db, creative_id, user_org_ids=scope)
