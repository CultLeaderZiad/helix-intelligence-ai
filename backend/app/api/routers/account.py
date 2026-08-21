import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.schemas.account import TrialStatusResponse
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.usage_log import UsageLog
from app.services.ai.ai_router import TRIAL_DAILY_REQUEST_LIMIT

router = APIRouter()

@router.get("/trial-status", response_model=TrialStatusResponse)
async def get_trial_status(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    now = datetime.datetime.now(datetime.timezone.utc)
    
    is_active = False
    days_remaining = 0
    
    if current_user.trial_expires_at:
        if now < current_user.trial_expires_at:
            is_active = True
            delta = current_user.trial_expires_at - now
            days_remaining = max(0, delta.days)

    # Get today's usage
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(func.count(UsageLog.id)).where(
        UsageLog.user_id == current_user.id,
        UsageLog.created_at >= today_start
    )
    usage_count = await db.scalar(query) or 0
    
    return TrialStatusResponse(
        active=is_active,
        days_remaining=days_remaining,
        requests_used=usage_count,
        requests_limit=TRIAL_DAILY_REQUEST_LIMIT
    )
