from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.webhook_event import WebhookEvent
from app.models.media_job import MediaGenerationJob
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

TERMINAL = {"completed", "failed", "nsfw", "canceled"}
def _extract_result_url(payload: dict) -> str | None:
    """Official webhook nests media under payload; status API may be top-level."""
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    images = body.get("images") or payload.get("images") or []
    video = body.get("video") or payload.get("video")

    if images and isinstance(images, list) and isinstance(images[0], dict):
        return images[0].get("url")
    if isinstance(video, dict):
        return video.get("url")
    return None

@router.post("/higgsfield")
async def higgsfield_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    request_id = payload.get("request_id")
    job_status = payload.get("status")

    if not request_id or not job_status:
        logger.warning("Invalid Higgsfield webhook envelope: %s", payload)
        # 200 so permanent junk does not retry forever if they treat 4xx as permanent
        return {"status": "ignored"}

    # Idempotency: same request_id + status
    existing = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.request_id == request_id,
            WebhookEvent.status == job_status,
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Duplicate webhook %s status=%s", request_id, job_status)
        return {"status": "ok"}

    event = WebhookEvent(
        request_id=request_id,
        provider="higgsfield",
        status=job_status,
        payload=payload,
    )
    db.add(event)
    await db.commit()

    job_result = await db.execute(
        select(MediaGenerationJob).where(
            MediaGenerationJob.provider_job_id == request_id
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        logger.warning("Webhook for unknown request_id=%s", request_id)
        return {"status": "ok"}

    if job.status in ("completed", "failed", "nsfw"):
        return {"status": "ok"}

    if job_status == "completed":
        result_url = _extract_result_url(payload)
        if result_url:
            job.status = "completed"
            job.result_url = result_url  # persist CDN URL (survives Render disk wipe)
            # Optional mirror (best-effort; do not block webhook)
            try:
                from app.services.storage_service import store_media_from_url
                import asyncio
                asyncio.create_task(store_media_from_url(job.id, result_url))
            except Exception as e:
                logger.warning("Optional store_media failed: %s", e)
        else:
            job.status = "failed"
            job.error_message = "completed webhook missing media URL"
    elif job_status in ("failed", "nsfw", "canceled"):
        job.status = "failed" if job_status != "nsfw" else "nsfw"
        err = payload.get("error")
        job.error_message = (
            err if isinstance(err, str) else f"Higgsfield status: {job_status}"
        )

    await db.commit()
    return {"status": "ok"}
