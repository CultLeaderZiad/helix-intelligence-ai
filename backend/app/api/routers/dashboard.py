from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services import dashboard_service

router = APIRouter()

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await dashboard_service.get_dashboard_metrics(db)
