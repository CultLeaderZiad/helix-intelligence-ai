from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.admin import AdminOverviewStats, AdminJobRow, AdminSystemHealth
from app.services import admin_service
from app.core.deps import get_db, get_current_admin
from app.models.user import User

router = APIRouter()

# Dependency injection enforces admin role for all routes in this router
# Typically done in router include, but explicitly adding here for clarity if needed, 
# or we can rely on dependencies param when including the router.
# Using Depends(get_current_admin) on each route for now.

@router.get("/overview/stats", response_model=AdminOverviewStats)
async def get_overview(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_overview(db)

@router.get("/jobs", response_model=List[AdminJobRow])
async def list_jobs(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.list_jobs(db)

@router.get("/system/health", response_model=AdminSystemHealth)
async def get_health(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return await admin_service.get_health(db)

