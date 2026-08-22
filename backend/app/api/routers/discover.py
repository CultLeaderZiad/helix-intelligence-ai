from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.discover import SearchParams, Job
from app.schemas.creative import Creative
from app.schemas.common import Paginated
from app.services import discover_service, creative_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/jobs", response_model=Job)
async def search(
    params: SearchParams, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await discover_service.trigger_search(db, params, current_user.id, background_tasks)

@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await discover_service.get_job_status(db, job_id)

@router.get("/jobs/{job_id}/results", response_model=Paginated[Creative])
async def get_job_results(
    job_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await creative_service.list_creatives(db, job_id=job_id, page=page, page_size=page_size)

@router.get("/jobs", response_model=Paginated[Job])
async def list_jobs(
    page: int = 1,
    page_size: int = 8,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await discover_service.list_recent_jobs(db, current_user.id, page, page_size)

