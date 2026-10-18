from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user, require_feature
from app.models.user import User
from app.schemas.media import MediaGenerationRequest, MediaGenerationJobResponse
from app.services import media_service
from app.services.storage_service import resolve_stored_url, store_media_bytes

router = APIRouter()


def _token_version(user: User) -> str:
    metadata = getattr(user, "signup_metadata", None) or {}
    try:
        return str(int(metadata.get("token_version", 1)))
    except (TypeError, ValueError):
        return "1"


def _present_job(job, user: User) -> dict:
    payload = MediaGenerationJobResponse.model_validate(job).model_dump(mode="json")
    payload["result_url"] = resolve_stored_url(
        payload.get("result_url"),
        org_id=getattr(job, "org_id", "") or "",
        user_id=user.id,
        token_version=_token_version(user),
    )
    return payload

@router.post("/jobs", response_model=MediaGenerationJobResponse, dependencies=[Depends(require_feature("create"))])
async def create_media_job(
    request: MediaGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await media_service.create_media_job(db, current_user, request)
    return _present_job(job, current_user)

@router.get("/models")
async def get_available_models():
    """Returns the semantic capability catalogue."""
    from app.services.media.modes import list_available_capabilities
    return list_available_capabilities()

@router.get("/providers")
async def get_media_providers():
    """Returns active media providers."""
    return [
        {
            "id": "gemini",
            "name": "Gemini (managed key or BYOK)",
            "capabilities": ["IMAGE_FAST", "IMAGE_PREMIUM", "IMAGE_CINEMATIC", "VIDEO_FAST", "VIDEO_STANDARD", "VIDEO_FIRST_LAST_FAST", "VIDEO_FIRST_LAST_STANDARD"],
            "status": "active"
        },
        {
            "id": "pollinations",
            "name": "Pollinations (video fallback)",
            "capabilities": ["VIDEO_FAST", "VIDEO_STANDARD"],
            "status": "active"
        }
    ]

@router.get("/jobs/{job_id}", response_model=MediaGenerationJobResponse, dependencies=[Depends(require_feature("create"))])
async def get_media_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await media_service.get_media_job(db, current_user, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _present_job(job, current_user)

@router.post("/jobs/{job_id}/cancel")
async def cancel_media_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await media_service.get_media_job(db, current_user, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in ("completed", "failed", "canceled"):
        return {"success": False, "message": f"Job already {job.status}", "status": job.status, "job_id": job_id}
    job.status = "canceled"
    await db.commit()
    return {"success": True, "message": "Job canceled", "job_id": job_id, "status": "canceled"}


@router.post("/upload", dependencies=[Depends(require_feature("create"))])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Enforce strict 2MB limit via streaming chunk read
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    CHUNK_SIZE = 64 * 1024  # 64KB
    
    total_bytes = 0
    buffer = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum limit of 2MB."
            )
        buffer.extend(chunk)
    content = bytes(buffer)
        
    mime_type = file.content_type or ""
    if not (mime_type.startswith("image/jpeg") or mime_type.startswith("image/png") or mime_type.startswith("image/jpg") or mime_type.startswith("image/webp")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload JPG, PNG, or WEBP images."
        )
        
    url = await store_media_bytes("upload", content, mime_type)
    url = resolve_stored_url(url, user_id=current_user.id, token_version=_token_version(current_user))
    return {"url": url}
