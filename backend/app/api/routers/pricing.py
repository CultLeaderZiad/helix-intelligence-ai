"""Public pricing: plans an admin marked listed, plus the free-trial terms. No auth."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.pricing import PublicPricing
from app.services import admin_service

router = APIRouter()


@router.get("", response_model=PublicPricing)
async def public_pricing(db: AsyncSession = Depends(get_db)):
    return await admin_service.list_public_pricing(db)
