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
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def store_media_from_url(job_id: str, source_url: str):
    """
    Downloads media from Higgsfield and stores it.
    Since we don't have S3 credentials, we store it in a local static directory.
    WARNING: On Render free tier, this is ephemeral and will be wiped.
    """
    try:
        logger.info(f"Downloading media for job {job_id} from {source_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            ext = ".mp4" if "video" in content_type else ".png" if "png" in content_type else ".jpg"
            
            filename = f"{job_id}_{uuid.uuid4().hex[:8]}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            with open(file_path, "wb") as f:
                f.write(response.content)
                
            # Base URL for static files (assumes we mount /uploads in main.py)
            # Default to Render URL or localhost depending on environment
            app_url = os.environ.get("VITE_API_BASE_URL", "http://localhost:8000/api")
            app_url = app_url.replace("/api", "")
            
            final_url = f"{app_url}/uploads/{filename}"
            logger.info(f"Stored media for job {job_id} at {final_url}")
            
            # Update DB with new URL
            async with async_session_maker() as db:
                result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.result_url = final_url
                    await db.commit()
    except Exception as e:
        logger.error(f"Failed to download/store media for job {job_id}: {e}")
