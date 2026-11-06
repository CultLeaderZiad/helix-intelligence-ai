"""Read the workspace's permanent ad archive (flag `discover`)."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_feature
from app.models.user import User
from app.services import archive_service

router = APIRouter(dependencies=[Depends(require_feature("discover"))])


@router.get("")
async def list_archive(
    page: int = 1,
    page_size: int = 50,
    brand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await archive_service.list_entries(db, current_user, page=page, page_size=page_size, brand=brand)


@router.get("/by-creative/{creative_id}")
async def archive_for_creative(
    creative_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await archive_service.get_for_creative(db, current_user, creative_id)
