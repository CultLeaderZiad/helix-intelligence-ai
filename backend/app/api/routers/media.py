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

@router.get("/models")
async def get_available_models():
    """Returns the semantic capability catalogue."""
    from app.services.media.higgsfield_registry import list_available_capabilities
    return list_available_capabilities()

@router.get("/providers")
async def get_media_providers():
    """Returns active media providers."""
    return [
        {
            "id": "higgsfield",
            "name": "Higgsfield AI",
            "capabilities": ["IMAGE_FAST", "IMAGE_PREMIUM", "IMAGE_CINEMATIC", "VIDEO_FAST", "VIDEO_STANDARD", "VIDEO_FIRST_LAST_FAST", "VIDEO_FIRST_LAST_STANDARD"],
            "status": "active"
        }
    ]

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

@router.post("/jobs/{job_id}/cancel")
async def cancel_media_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"success": True, "message": "Job cancellation requested", "job_id": job_id}
