import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.media_job import MediaGenerationJob
from app.schemas.media import MediaGenerationRequest
from app.models.user import User
from app.models.organization import Organization
from app.services.billing_service import (
    assert_can_generate_image,
    record_image_generated,
    record_video_generated,
)
from app.services.provider_resolver import resolve_image_provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.storage_service import store_media_bytes
from app.services.media.mode_registry import resolve_mode_spec
from app.core.config import settings

logger = logging.getLogger(__name__)

async def gemini_generate_media_task(job_id: str, user_id: str, org_id: str):
    """
    Executes synchronous/async Gemini image generation in background task.
    Resolves Managed vs BYOK provider without leaking credentials.
    Persists binary image bytes and updates MediaGenerationJob status.
    Increments daily usage counter only upon verified success.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        org_result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = org_result.scalar_one_or_none()

        if not user or not org:
            job.status = "failed"
            job.error_message = "User or organization not found"
            await db.commit()
            return

        # Resolve provider (Managed or BYOK)
        provider_instance, credential_mode = await resolve_image_provider(db, user, org)

        params = dict(job.parameters or {})
        
        # Override with per-request BYOK if provided in parameters
        custom_api_key = params.get("custom_api_key")
        custom_model = params.get("custom_model")
        
        if custom_api_key:
            provider_instance = GeminiProvider(api_key=custom_api_key)
            credential_mode = "byok_request"
            
        if custom_model:
            provider_instance.image_model = custom_model

        job.status = "running"
        params["credential_mode"] = credential_mode
        params["model"] = provider_instance.image_model
        job.parameters = params
        await db.commit()

        try:
            aspect_ratio = params.get("aspect_ratio", "1:1")
            reference_images = list(params.get("reference_images") or [])
            if params.get("start_image_url"):
                reference_images.append(params.get("start_image_url"))

            mode = params.get("mode")
            mode_spec = resolve_mode_spec(mode) if mode else {}
            media_category = mode_spec.get("output_type", "image")

            if media_category == "video":
                # If provider is Pollinations, use it. Otherwise fallback to Pollinations for video
                if hasattr(provider_instance, "generate_video"):
                    gen_result = await provider_instance.generate_video(
                        prompt=job.prompt,
                        aspect_ratio=aspect_ratio,
                        model=params.get("custom_model") or "wan-fast"
                    )
                else:
                    from app.services.ai.pollinations_provider import PollinationsProvider
                    temp_provider = PollinationsProvider()
                    gen_result = await temp_provider.generate_video(
                        prompt=job.prompt,
                        aspect_ratio=aspect_ratio,
                        model=params.get("custom_model") or "wan-fast"
                    )
            else:
                gen_result = await provider_instance.generate_image(
                    prompt=job.prompt,
                    reference_images=reference_images,
                    aspect_ratio=aspect_ratio,
                )

            # Store binary media
            media_bytes = gen_result.get("data")
            mime_type = gen_result.get("mime_type", "video/mp4" if media_category == "video" else "image/png")
            final_url = await store_media_bytes(job.id, media_bytes, mime_type)

            job.status = "completed"
            job.result_url = final_url
            await db.commit()

            # Increment usage counters only on success
            if media_category == "video":
                await record_video_generated(db, user, org, job_id=job.id)
            else:
                await record_image_generated(db, user, org, job_id=job.id)

            logger.info(
                "Gemini/Pollinations job %s completed successfully (%s mode): %s",
                job_id,
                credential_mode,
                final_url
            )

        except Exception as e:
            logger.error("Gemini image generation failed for job %s: %s", job_id, str(e))
            job.status = "failed"
            err_msg = str(e)
            
            if credential_mode == "byok":
                # Explicit error for customer BYOK key — NO SILENT FALLBACK
                job.error_message = "Your connected Gemini account is unavailable. Check your API key or Google quota."
            elif "provider_rate_limited" in err_msg or "429" in err_msg:
                job.error_message = "Gemini provider is currently rate-limited. Please try again shortly."
            elif "API key" in err_msg:
                job.error_message = "Gemini API key is invalid or unauthorized."
            else:
                job.error_message = err_msg[:200]
                
            await db.commit()


async def mock_generate_media_task(job_id: str):
    await asyncio.sleep(2)
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.result_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1024"
            await db.commit()


async def create_media_job(db: AsyncSession, user: User, request: MediaGenerationRequest) -> MediaGenerationJob:
    """
    Creates and initiates a media generation job.
    All generation routes through Gemini (images) / Pollinations (video) —
    Higgsfield has been removed as a provider.
    """
    parameters = dict(request.parameters or {})
    if request.mode and "mode" not in parameters:
        parameters["mode"] = request.mode

    mode = parameters.get("mode") or request.mode or "premium_ad"
    mode_spec = resolve_mode_spec(mode)
    media_category = mode_spec.get("output_type", "image")

    # 1. Strict Server-side Trial & Quota Gatekeeper
    org, plan = await assert_can_generate_image(
        db,
        user=user,
        media_type=media_category,
        lock_row=True
    )

    requested_provider = (request.provider or "").lower()

    # All generation routes through Gemini/Pollinations regardless of what
    # the client requests, except an explicit mock request in mock mode.
    if requested_provider == "mock" and settings.USE_MOCKS:
        provider = "mock"
    else:
        provider = "gemini"

    # 2. Persist MediaGenerationJob
    job = MediaGenerationJob(
        user_id=user.id,
        org_id=org.id,
        prompt=request.prompt,
        provider=provider,
        parameters=parameters,
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 3. Dispatch Provider Task
    if provider == "mock":
        asyncio.create_task(mock_generate_media_task(job.id))
    else:
        asyncio.create_task(gemini_generate_media_task(job.id, user.id, org.id))

    return job


async def get_media_job(db: AsyncSession, user: User, job_id: str) -> Optional[MediaGenerationJob]:
    result = await db.execute(
        select(MediaGenerationJob).where(MediaGenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    return job
