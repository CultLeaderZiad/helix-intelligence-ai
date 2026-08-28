import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.media_job import MediaGenerationJob
from app.schemas.media import MediaGenerationRequest
from app.models.user import User
from app.services.billing_service import get_or_create_default_org
from app.services.media.higgsfield_provider import HiggsfieldProvider

logger = logging.getLogger(__name__)

async def mock_generate_media_task(job_id: str):
    """
    Simulates a background generation task.
    In real implementation, this might just send the API request to Higgsfield
    and another webhook would update the status. For mock, we sleep and update.
    """
    await asyncio.sleep(5)
    
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if job:
            job.status = "completed"
            job.result_url = "https://www.w3schools.com/html/mov_bbb.mp4" # Mock video
            await db.commit()

async def higgsfield_generate_media_task(job_id: str):
    from app.db.session import async_session_maker
    
    provider = HiggsfieldProvider()
    
    async with async_session_maker() as db:
        result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            return
            
        try:
            # 1. Start generation
            import os
            logger.info(f"Starting Higgsfield generation for job {job_id}")
            
            # Construct webhook URL
            app_url = os.environ.get("VITE_API_BASE_URL", "http://localhost:8000/api")
            webhook_url = f"{app_url}/webhooks/higgsfield"
            
            params = job.parameters or {}
            params["webhook"] = webhook_url
            
            request_id = await provider.generate_media(job.prompt, params)
            
            job.provider_job_id = request_id
            job.status = "in_progress"
            await db.commit()
            
            # 2. Polling fallback
            max_attempts = 60
            for attempt in range(max_attempts):
                await asyncio.sleep(2.0)
                
                # Check DB first to see if webhook already processed it
                # We need to refresh the job from the DB
                await db.refresh(job)
                if job.status in ["completed", "failed", "nsfw"]:
                    logger.info(f"Job {job_id} already completed by webhook (status: {job.status})")
                    return
                
                status_info = await provider.check_status(request_id)
                status = status_info.get("status")
                
                if status == "completed":
                    job.status = "completed"
                    # Trigger storage service manually since webhook missed it
                    from app.services.storage_service import store_media_from_url
                    result_url = status_info.get("url")
                    if result_url:
                        asyncio.create_task(store_media_from_url(job.id, result_url))
                    await db.commit()
                    logger.info(f"Job {job_id} completed successfully via polling fallback")
                    return
                elif status in ["failed", "nsfw"]:
                    job.status = "failed"
                    job.error_message = f"Higgsfield status: {status}"
                    await db.commit()
                    logger.error(f"Job {job_id} failed with status: {status}")
                    return
                    
            # Timeout
            job.status = "failed"
            job.error_message = "Polling timed out"
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error in Higgsfield generation task: {e}")
            job.status = "failed"
            job.error_message = str(e)
            await db.commit()


async def create_media_job(db: AsyncSession, user: User, request: MediaGenerationRequest) -> MediaGenerationJob:
    org = await get_or_create_default_org(db, user)
    
    job = MediaGenerationJob(
        user_id=user.id,
        org_id=org.id,
        prompt=request.prompt,
        provider=request.provider,
        parameters=request.parameters,
        status="pending"
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    if request.provider == "mock":
        # Launch background task for mock
        asyncio.create_task(mock_generate_media_task(job.id))
    elif request.provider == "higgsfield":
        # Launch real background task
        asyncio.create_task(higgsfield_generate_media_task(job.id))
        
    return job

async def get_media_job(db: AsyncSession, user: User, job_id: str) -> MediaGenerationJob:
    org = await get_or_create_default_org(db, user)
    
    result = await db.execute(
        select(MediaGenerationJob)
        .where(MediaGenerationJob.id == job_id, MediaGenerationJob.org_id == org.id)
    )
    job = result.scalar_one_or_none()
    return job
