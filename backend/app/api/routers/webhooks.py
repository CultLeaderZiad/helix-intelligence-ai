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

async def _mirror_to_storage(job_id: str, source_url: str) -> None:
    """Re-host provider media on our own storage and point the job at it.

    Higgsfield's URLs are temporary, so keeping only their link means the
    asset disappears later. The previous version scheduled the download but
    discarded its result, leaving the job pointing at the provider forever;
    this writes the stored URL back.
    """
    from app.db.session import async_session_maker
    from app.services.storage_service import store_media_from_url

    try:
        stored_url = await store_media_from_url(job_id, source_url)
        if not stored_url or stored_url == source_url:
            return
        async with async_session_maker() as db:
            job = (
                await db.execute(
                    select(MediaGenerationJob).where(MediaGenerationJob.id == job_id)
                )
            ).scalar_one_or_none()
            if job:
                job.result_url = stored_url
                await db.commit()
                logger.info("Mirrored media for job %s to %s", job_id, stored_url)
    except Exception as e:
        logger.warning("Media mirror failed for job %s: %s", job_id, e)


@router.post("/higgsfield")
async def higgsfield_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # ── Authentication: verify the HMAC-SHA256 signature BEFORE trusting any
    # field in the body. An unsigned callback can otherwise forge a job
    # completion (or mass-fail jobs) with nothing but a guessable request_id.
    from app.core.config import settings as _settings
    from app.core.security import verify_hmac_signature

    if not _settings.HF_WEBHOOK_SECRET:
        # Closed by default: refuse every callback until a secret is configured
        # rather than accept unsigned forgeries. Jobs stay "running" and are
        # swept by the reconciler until this is set.
        logger.error("Higgsfield webhook received but HF_WEBHOOK_SECRET is not configured — refusing (503).")
        raise HTTPException(status_code=503, detail="Webhook endpoint is not configured")

    body = await request.body()
    signature = (
        request.headers.get("x-higgsfield-signature")
        or request.headers.get("x-signature")
        or request.headers.get("x-hub-signature-256")
        or ""
    )
    if not verify_hmac_signature(body, signature, _settings.HF_WEBHOOK_SECRET):
        logger.warning("Higgsfield webhook signature verification FAILED from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


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
            # Provider URL first so the job is never left without a reference;
            # the mirror below replaces it with our own copy once stored.
            job.result_url = result_url
            try:
                import asyncio

                asyncio.create_task(_mirror_to_storage(job.id, result_url))
            except Exception as e:
                logger.warning("Could not schedule media mirror: %s", e)
        else:
            job.status = "failed"
            job.failure_kind = "error"
            job.error_message = "completed webhook missing media URL"
    elif job_status in ("failed", "nsfw", "canceled"):
        job.status = "failed" if job_status != "nsfw" else "nsfw"
        job.failure_kind = "error"
        err = payload.get("error")
        job.error_message = (
            err if isinstance(err, str) else f"Higgsfield status: {job_status}"
        )

    await db.commit()
    return {"status": "ok"}
