from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.media import MediaGenerationRequest, MediaGenerationJobResponse
from app.services import media_service
from app.services.storage_service import store_media_bytes

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
    """Returns the available Create modes (image/video)."""
    from app.services.media.mode_registry import MODE_OUTPUT_TYPES
    return [{"mode": mode, "output_type": output_type} for mode, output_type in MODE_OUTPUT_TYPES.items()]

@router.get("/providers")
async def get_media_providers():
    """Returns active media providers."""
    return [
        {
            "id": "gemini",
            "name": "Google Gemini",
            "capabilities": ["image"],
            "status": "active"
        },
        {
            "id": "pollinations",
            "name": "Pollinations",
            "capabilities": ["video"],
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


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Enforce strict 2MB limit
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 2MB."
        )
        
    mime_type = file.content_type or ""
    if not (mime_type.startswith("image/jpeg") or mime_type.startswith("image/png") or mime_type.startswith("image/jpg") or mime_type.startswith("image/webp")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload JPG, PNG, or WEBP images."
        )
        
    url = await store_media_bytes("upload", content, mime_type)
    return {"url": url}
