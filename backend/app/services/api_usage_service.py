from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime
from app.models.api_usage import ExternalApiUsage
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DAILY_ORG_API_CAP = 500

class APILimitExceeded(Exception):
    pass

async def check_global_cap_and_log_preflight(
    db: AsyncSession, 
    provider: str, 
    org_id: str, 
    user_id: str, 
    query: str, 
    max_records: int, 
    estimated_cost: float,
    daily_cap: Optional[int] = None
) -> ExternalApiUsage:
    """
    Checks if the organization's daily API cap is exceeded (F50).
    Only counts active / successful calls for the organization (status != 'failed').
    If not exceeded, creates an 'attempted' pre-flight log and returns it.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    cap = daily_cap or DEFAULT_DAILY_ORG_API_CAP

    # Check org-scoped cap for today (ignoring failed calls)
    count_query = select(func.count(ExternalApiUsage.id)).where(
        ExternalApiUsage.org_id == org_id,
        ExternalApiUsage.created_at >= start_of_day,
        ExternalApiUsage.status != "failed"
    )
    if hasattr(db, "scalar"):
        today_count = (await db.scalar(count_query)) or 0
    else:
        res = await db.execute(count_query)
        today_count = res.scalar() if hasattr(res, "scalar") else 0
    
    if today_count >= cap:
        logger.error(f"Organization {org_id} daily API cap exceeded: {today_count}/{cap} calls today.")
        raise APILimitExceeded(f"Daily API limit reached ({today_count}/{cap}). Quota resets at 00:00 UTC.")
        
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
