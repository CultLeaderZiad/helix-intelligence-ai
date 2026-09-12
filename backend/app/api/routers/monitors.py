from typing import Any, Dict, List, Optional
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services import monitor_service
from app.services.billing_service import get_or_create_default_org

router = APIRouter()


class MonitorCreate(BaseModel):
    query: str = Field(..., min_length=1, max_length=300)
    name: Optional[str] = Field(None, max_length=200)
    cadence: str = "daily"
    filters: Optional[Dict[str, Any]] = None
    notify_in_app: bool = True
    notify_email: bool = False


class MonitorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    cadence: Optional[str] = None
    status: Optional[str] = None
    notify_in_app: Optional[bool] = None
    notify_email: Optional[bool] = None


async def _org_id(db: AsyncSession, user: User) -> str:
    org = await get_or_create_default_org(db, user)
    return org.id


@router.get("")
@router.get("/")
async def list_monitors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return await monitor_service.list_monitors(db, await _org_id(db, current_user))


@router.post("", status_code=201)
@router.post("/", status_code=201)
async def create_monitor(
    payload: MonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return await monitor_service.create_monitor(
        db,
        user=current_user,
        org_id=await _org_id(db, current_user),
        name=payload.name or "",
        query=payload.query,
        cadence=payload.cadence,
        filters=payload.filters,
        notify_in_app=payload.notify_in_app,
        notify_email=payload.notify_email,
    )


@router.get("/events")
async def list_events(
    monitor_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return await monitor_service.get_monitor_events(
        db, await _org_id(db, current_user), monitor_id=monitor_id, limit=limit
    )


@router.patch("/{monitor_id}")
async def update_monitor(
    monitor_id: str,
    payload: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return await monitor_service.update_monitor(
        db, monitor_id, await _org_id(db, current_user), payload.model_dump(exclude_unset=True)
    )


@router.delete("/{monitor_id}")
async def delete_monitor(
    monitor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return await monitor_service.delete_monitor(db, monitor_id, await _org_id(db, current_user))


@router.post("/{monitor_id}/run")
async def run_monitor_now(
    monitor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return await monitor_service.run_now(db, monitor_id, await _org_id(db, current_user))


@router.post("/tick")
async def tick(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
) -> Dict[str, Any]:
    """Dispatch every monitor that is due.

    Deliberately not tied to Render Cron Jobs, which are a paid service type.
    Any scheduler that can send an HTTP POST with a header works, including the
    free ones already used to keep the instance warm.

    Returns as soon as the runs are dispatched — a discovery run takes minutes,
    far longer than a cron provider will hold a request open.
    """
    if not settings.CRON_SECRET:
        # Closed by default: an unconfigured deployment must not expose a way
        # to spend an organisation's credits.
        raise HTTPException(
            status_code=503,
            detail="Monitor scheduling is not configured (CRON_SECRET is unset).",
        )
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret, settings.CRON_SECRET):
        raise HTTPException(status_code=403, detail="Invalid cron secret.")

    return await monitor_service.tick()
