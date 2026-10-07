import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from app.core.deps import get_db, get_current_user, get_current_admin, get_optional_user
from app.models.user import User
from app.models.app_update import AppUpdate
from app.schemas.app_update import (
    AppUpdateCreate,
    AppUpdateUpdate,
    AppUpdateResponse,
)

router = APIRouter()

def normalize_to_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    """Properly converts timezone-aware datetime to UTC without stripping offsets (F69)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(datetime.timezone.utc)
    return dt.replace(tzinfo=datetime.timezone.utc)

# ---------------------------------------------------------------------------
# Public & Authenticated Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[AppUpdateResponse])
async def list_published_updates(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    List all published updates currently active or within schedule.
    Unauthenticated callers only receive updates flagged with show_on_public=True (F48).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    conditions = [
        AppUpdate.is_published == True,
        or_(AppUpdate.starts_at == None, AppUpdate.starts_at <= now),
        or_(AppUpdate.ends_at == None, AppUpdate.ends_at >= now),
    ]
    if user is None:
        conditions.append(AppUpdate.show_on_public == True)

    query = select(AppUpdate).where(*conditions).order_by(desc(AppUpdate.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/banner", response_model=Optional[AppUpdateResponse])
async def get_active_banner(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Returns the single active public/app-wide banner:
    Highest priority = most recent published update with show_as_banner=True
    and within its scheduled start/end times.
    Unauthenticated callers only receive banners with show_on_public=True (F48).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    conditions = [
        AppUpdate.is_published == True,
        AppUpdate.show_as_banner == True,
        or_(AppUpdate.starts_at == None, AppUpdate.starts_at <= now),
        or_(AppUpdate.ends_at == None, AppUpdate.ends_at >= now),
    ]
    if user is None:
        conditions.append(AppUpdate.show_on_public == True)

    query = select(AppUpdate).where(*conditions).order_by(desc(AppUpdate.created_at)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Admin Endpoints (Admin Only)
# ---------------------------------------------------------------------------

@router.get("/admin/all", response_model=List[AppUpdateResponse])
async def admin_list_updates(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin: List all updates (published, draft, banners, and scheduled).
    """
    query = select(AppUpdate).order_by(desc(AppUpdate.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/admin", response_model=AppUpdateResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_update(
    update_in: AppUpdateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin: Create a new update or banner announcement.
    """
    create_data = update_in.model_dump()
    if create_data.get("starts_at") is not None:
        create_data["starts_at"] = normalize_to_utc(create_data["starts_at"])
    if create_data.get("ends_at") is not None:
        create_data["ends_at"] = normalize_to_utc(create_data["ends_at"])

    update = AppUpdate(
        **create_data,
        created_by=admin.id,
    )
    db.add(update)
    await db.commit()
    await db.refresh(update)
    return update


@router.get("/admin/{update_id}", response_model=AppUpdateResponse)
async def admin_get_update(
    update_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin: Get specific update by ID.
    """
    result = await db.execute(select(AppUpdate).where(AppUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")
    return update


@router.patch("/admin/{update_id}", response_model=AppUpdateResponse)
@router.put("/admin/{update_id}", response_model=AppUpdateResponse)
@router.post("/admin/{update_id}", response_model=AppUpdateResponse)
async def admin_update_update(
    update_id: str,
    update_in: AppUpdateUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin: Edit/toggle update (publish status, banner visibility, etc.).
    """
    result = await db.execute(select(AppUpdate).where(AppUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")

    update_data = update_in.model_dump(exclude_unset=True)
    if "starts_at" in update_data and update_data["starts_at"] is not None:
        update_data["starts_at"] = normalize_to_utc(update_data["starts_at"])
    if "ends_at" in update_data and update_data["ends_at"] is not None:
        update_data["ends_at"] = normalize_to_utc(update_data["ends_at"])

    for field, value in update_data.items():
        if hasattr(update, field):
            setattr(update, field, value)

    update.updated_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(update)
    return update


@router.delete("/admin/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_update(
    update_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin: Delete an update.
    """
    result = await db.execute(select(AppUpdate).where(AppUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")

    await db.delete(update)
    await db.commit()
    return None
