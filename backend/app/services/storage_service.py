import httpx
import logging
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.media_job import MediaGenerationJob
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)

# Temporary local storage location for Render. 
# WARNING: This will be wiped upon instance restart/deploy!
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def store_media_bytes(job_id: str, data: bytes, mime_type: str = "image/png") -> str:
    """
    Persists binary image bytes directly to local storage and returns public URL.
    """
    ext = ".jpg" if "jpeg" in mime_type or "jpg" in mime_type else ".webp" if "webp" in mime_type else ".png"
    filename = f"{job_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(data)

    from app.core.config import settings
    app_url = (
        os.environ.get("PUBLIC_API_BASE_URL")
        or getattr(settings, "PUBLIC_API_BASE_URL", "")
        or os.environ.get("VITE_API_BASE_URL", "http://localhost:8000/api")
    )
    app_url = app_url.rstrip("/").replace("/api", "")
    final_url = f"{app_url}/uploads/{filename}"
    return final_url

async def store_media_from_url(job_id: str, source_url: str) -> str:
    """
    Downloads media from an external URL and stores it locally.
    """
    try:
        logger.info(f"Downloading media for job {job_id} from {source_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return await store_media_bytes(job_id, response.content, content_type)
    except Exception as e:
        logger.error(f"Failed to download/store media for job {job_id}: {e}")
        return source_url


