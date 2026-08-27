import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.media_job import MediaGenerationJob
from app.schemas.media import MediaGenerationRequest
from app.models.user import User
from app.services.billing_service import get_or_create_default_org

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
        
    return job

async def get_media_job(db: AsyncSession, user: User, job_id: str) -> MediaGenerationJob:
    org = await get_or_create_default_org(db, user)
    
    result = await db.execute(
        select(MediaGenerationJob)
        .where(MediaGenerationJob.id == job_id, MediaGenerationJob.org_id == org.id)
    )
    job = result.scalar_one_or_none()
    return job
