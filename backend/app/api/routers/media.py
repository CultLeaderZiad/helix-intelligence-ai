from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.media import MediaGenerationRequest, MediaGenerationJobResponse
from app.services import media_service

router = APIRouter()

@router.post("/jobs", response_model=MediaGenerationJobResponse)
async def create_media_job(
    request: MediaGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await media_service.create_media_job(db, current_user, request)
    return job

@router.get("/jobs/{job_id}", response_model=MediaGenerationJobResponse)
async def get_media_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await media_service.get_media_job(db, current_user, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
