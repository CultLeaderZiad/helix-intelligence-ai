from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.webhook_event import WebhookEvent
from app.models.media_job import MediaGenerationJob
from app.services import media_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/higgsfield")
async def higgsfield_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    request_id = payload.get("request_id")
    job_status = payload.get("status")

    if not request_id or not job_status:
        # Ignore invalid payloads but return 200 to prevent retries if it's junk
        logger.warning(f"Invalid webhook payload from Higgsfield: {payload}")
        return {"status": "ignored"}

    # Check for idempotency
    existing_event = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.request_id == request_id,
            WebhookEvent.status == job_status
        )
    )
    if existing_event.scalar_one_or_none():
        logger.info(f"Duplicate webhook received for {request_id} with status {job_status}")
        return {"status": "ok"}

    # Record event
    event = WebhookEvent(
        request_id=request_id,
        provider="higgsfield",
        status=job_status,
        payload=payload
    )
    db.add(event)
    await db.commit()

    # Find the corresponding job
    job_result = await db.execute(
        select(MediaGenerationJob).where(MediaGenerationJob.provider_job_id == request_id)
    )
    job = job_result.scalar_one_or_none()

    if not job:
        logger.warning(f"Webhook received for unknown request_id: {request_id}")
        return {"status": "ok"}

    # Update job if not already in a terminal state or if we are progressing to one
    if job.status not in ["completed", "failed", "nsfw"]:
        if job_status == "completed":
            job.status = "completed"
            
            # Extract URL from payload depending on V2Response structure
            images = payload.get("images", [])
            video = payload.get("video")
            
            result_url = None
            if images and isinstance(images, list) and len(images) > 0:
                result_url = images[0].get("url")
            elif video and isinstance(video, dict):
                result_url = video.get("url")
            
            if result_url:
                # Trigger download and persistent storage task
                # Using local filesystem storage for now since AWS S3 isn't configured
                from app.services.storage_service import store_media_from_url
                import asyncio
                asyncio.create_task(store_media_from_url(job.id, result_url))
            else:
                job.status = "failed"
                job.error_message = "No result URL provided in completed webhook payload"
                
        elif job_status in ["failed", "nsfw"]:
            job.status = "failed"
            job.error_message = f"Higgsfield status: {job_status}"
            
        await db.commit()
        
    return {"status": "ok"}
