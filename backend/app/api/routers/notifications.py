from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services import notification_service

router = APIRouter()

@router.get("")
@router.get("/")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await notification_service.list_notifications(db, current_user.id)

@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await notification_service.mark_as_read(db, current_user.id, notification_id)

@router.post("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await notification_service.mark_all_as_read(db, current_user.id)
