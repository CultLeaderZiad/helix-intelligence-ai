from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime
from app.models.api_usage import ExternalApiUsage
import logging

logger = logging.getLogger(__name__)

DAILY_API_CAP = 20

class APILimitExceeded(Exception):
    pass

async def check_global_cap_and_log_preflight(
    db: AsyncSession, 
    provider: str, 
    org_id: str, 
    user_id: str, 
    query: str, 
    max_records: int, 
    estimated_cost: float
) -> ExternalApiUsage:
    """
    Checks if the global daily API cap is exceeded. 
    If not, creates an 'attempted' pre-flight log and returns it.
    """
    now = datetime.datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check global cap for today (across all paid providers)
    count_query = select(func.count(ExternalApiUsage.id)).where(
        ExternalApiUsage.created_at >= start_of_day
    )
    today_count = await db.scalar(count_query) or 0
    
    if today_count >= DAILY_API_CAP:
        logger.error(f"SYSTEM-WIDE DAILY API CAP EXCEEDED: {today_count} calls today.")
        raise APILimitExceeded("System-wide daily API limit reached. Please try again tomorrow.")
        
    # Pre-flight log
    usage_log = ExternalApiUsage(
        provider=provider,
        org_id=org_id,
        user_id=user_id,
        query=query,
        max_records_requested=max_records,
        estimated_cost_usd=estimated_cost,
        status="attempted"
    )
    db.add(usage_log)
    await db.commit()
    await db.refresh(usage_log)
    return usage_log

async def mark_api_usage_status(db: AsyncSession, usage_id: str, status: str):
    """
    Marks the pre-flight log as success or failed.
    """
    result = await db.execute(select(ExternalApiUsage).where(ExternalApiUsage.id == usage_id))
    log = result.scalar_one_or_none()
    if log:
        log.status = status
        await db.commit()
