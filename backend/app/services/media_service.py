import asyncio
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.media_job import MediaGenerationJob
from app.schemas.media import MediaGenerationRequest
from app.models.user import User
from app.models.organization import Organization
from app.services.billing_service import (
    get_or_create_default_org,
    assert_can_generate_image,
    record_image_generated,
    record_video_generated,
)
from app.services.provider_resolver import resolve_image_provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.storage_service import store_media_bytes
# (Higgsfield provider removed from the app - Gemini serves all generations)
from app.services.media.modes import resolve_mode_spec
from datetime import datetime, timezone
from app.core.runtime import BOOT_ID
from app.services.job_heartbeat import heartbeat
from app.core.config import settings

logger = logging.getLogger(__name__)


def _with_heartbeat(coro_factory, job_id: str):
    """Run a media task while holding a heartbeat on its row.

    Without this a generation interrupted by a restart stays 'pending' or
    'in_progress' forever and the Create page spins indefinitely.
    """
    async def runner():
        async with heartbeat("media_jobs", job_id):
            await coro_factory()

    return runner()

async def meter_media_success(job_id: str) -> None:
    """Increment the daily image/video quota and write a UsageLog for a
    COMPLETED media job - exactly once.

    A removed provider path used to mark jobs "completed"
    without calling the billing/usage layer, so paid generations never counted
    against quotas and never appeared in admin usage analytics. Idempotency:
    the Gemini path already writes a UsageLog with the job_id, so an existing
    row means "already metered".
    """
    from app.db.session import async_session_maker
    from app.models.usage_log import UsageLog
    from app.services.billing_service import (
        record_image_generated,
        record_video_generated,
    )

    try:
        async with async_session_maker() as db:
            job = (await db.execute(
                select(MediaGenerationJob).where(MediaGenerationJob.id == job_id)
            )).scalar_one_or_none()
            if not job:
                return
            already = (await db.execute(
                select(func.count(UsageLog.id)).where(
                    UsageLog.job_id == job_id,
                    UsageLog.operation.in_(("media_generate_image", "media_generate_video")),
                )
            )).scalar() or 0
            if already:
                return
            user = (await db.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
            org = (await db.execute(select(Organization).where(Organization.id == job.org_id))).scalar_one_or_none()
            if not user or not org:
                return
            params = job.parameters or {}
            mode_spec = resolve_mode_spec(params.get("mode")) if params.get("mode") else {}
            if mode_spec.get("output_type", "image") == "video":
                await record_video_generated(db, user, org, job_id=job.id)
            else:
                await record_image_generated(db, user, org, job_id=job.id)
            logger.info("Metered completed media job %s (%s)", job.id, mode_spec.get("output_type", "image"))
    except Exception as e:
        logger.error("Media metering failed for job %s: %s", job_id, e)


async def gemini_generate_media_task(job_id: str, user_id: str, org_id: str, custom_api_key: Optional[str] = None):
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
            job.failure_kind = "error"
            job.error_message = "User or organization not found"
            await db.commit()
            return

        # Check if job was already canceled before starting (F40)
        if job.status == "canceled":
            logger.info("Media job %s was canceled prior to start, aborting", job_id)
            return

        credential_mode = "managed"
        try:
            # Resolve provider (Managed or BYOK) (F82)
            provider_instance, credential_mode = await resolve_image_provider(db, user, org)

            params = dict(job.parameters or {})
            
            # Override with per-request BYOK if provided in parameters
            custom_api_key = custom_api_key or params.get("custom_api_key")  # in-memory key wins; legacy rows may still carry one
            custom_model = params.get("custom_model")
            
            if custom_api_key:
                provider_instance = GeminiProvider(api_key=custom_api_key)
                credential_mode = "byok_request"
                
            if custom_model:
                provider_instance.image_model = custom_model

            job.status = "running"
            job.owner_boot_id = BOOT_ID
            job.heartbeat_at = datetime.now(timezone.utc)
            params["credential_mode"] = credential_mode
            params["model"] = provider_instance.image_model
            job.parameters = params
            await db.commit()

            aspect_ratio = params.get("aspect_ratio", "1:1")
            reference_images = list(params.get("reference_images") or [])
            if params.get("start_image_url"):
                reference_images.append(params.get("start_image_url"))

            mode = params.get("mode")
            mode_spec = resolve_mode_spec(mode) if mode else {}
            media_category = mode_spec.get("output_type", "image")

            if media_category == "video":
                start_frame = params.get("start_frame") or params.get("start_image_url")
                end_frame = params.get("end_frame") or params.get("end_image_url")
                video_kwargs = {}
                if start_frame:
                    video_kwargs["start_frame"] = start_frame
                if end_frame:
                    video_kwargs["end_frame"] = end_frame

                # If provider is Pollinations, use it. Otherwise fallback to Pollinations for video (F39)
                if hasattr(provider_instance, "generate_video"):
                    gen_result = await provider_instance.generate_video(
                        prompt=job.prompt,
                        aspect_ratio=aspect_ratio,
                        model=params.get("custom_model") or "wan-fast",
                        **video_kwargs
                    )
                else:
                    from app.services.ai.pollinations_provider import PollinationsProvider
                    temp_provider = PollinationsProvider()
                    gen_result = await temp_provider.generate_video(
                        prompt=job.prompt,
                        aspect_ratio=aspect_ratio,
                        model=params.get("custom_model") or "wan-fast",
                        **video_kwargs
                    )
            else:
                try:
                    gen_result = await provider_instance.generate_image(
                        prompt=job.prompt,
                        reference_images=reference_images,
                        aspect_ratio=aspect_ratio,
                        seed=params.get("seed"),
                    )
                except Exception as img_err:
                    err_str = str(img_err).lower()
                    from app.services.ai.pollinations_provider import PollinationsProvider
                    if ("quota" in err_str or "rate limit" in err_str or "429" in err_str or "resourceexhausted" in err_str) and not isinstance(provider_instance, PollinationsProvider):
                        logger.warning(
                            "Primary image provider failed due to quota/rate limit: %s. Transparently falling back to Pollinations FLUX.",
                            img_err
                        )
                        fallback_provider = PollinationsProvider()
                        gen_result = await fallback_provider.generate_image(
                            prompt=job.prompt,
                            reference_images=reference_images,
                            aspect_ratio=aspect_ratio,
                            seed=params.get("seed"),
                            model="flux",
                        )
                    else:
                        raise

            # Store binary media
            media_bytes = gen_result.get("data")
            mime_type = gen_result.get("mime_type", "video/mp4" if media_category == "video" else "image/png")
            final_url = await store_media_bytes(job.id, media_bytes, mime_type)

            # Check if job was canceled while generation was running (F40)
            await db.refresh(job)
            if job.status == "canceled":
                logger.info("Media job %s was canceled during execution, skipping completion and usage recording", job.id)
                return

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
            logger.error("Media generation failed for job %s: %s", job_id, str(e))
            await db.refresh(job)
            if job.status == "canceled":
                return
            job.status = "failed"
            job.failure_kind = "error"
            err_msg = str(e)
            
            if credential_mode == "byok":
                # Explicit error for customer BYOK key — NO SILENT FALLBACK
                job.error_message = "Your connected Gemini account is unavailable. Check your API key or Google quota."
            elif "provider_rate_limited" in err_msg or "429" in err_msg:
                job.error_message = "Gemini provider is currently rate-limited. Please try again shortly."
            elif "API key" in err_msg:
                job.error_message = "Gemini API key is invalid or unauthorized."
            else:
                import re
                clean_msg = re.sub(r'([?&]key=)[^&\s]+', r'\1[REDACTED]', err_msg)
                if custom_api_key:
                    clean_msg = clean_msg.replace(custom_api_key, "[REDACTED]")
                job.error_message = clean_msg[:200]
                
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
    Uses Gemini for all image generations on trial, enforcing strict server-side limits.
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

    # Provider routing. The Higgsfield provider was removed from the app:
    # every generation runs through Gemini (managed key or BYOK), with the
    # in-task Pollinations fallback for video. Legacy "higgsfield" requests
    # are accepted and served by Gemini so existing clients keep working.
    if requested_provider == "mock" and settings.USE_MOCKS:
        provider = "mock"
    else:
        provider = "gemini"

    # SECURITY: per-request BYOK keys must never be persisted with the job or
    # echoed in job responses. Keep it in memory and hand it to the task only.
    request_api_key = parameters.pop("custom_api_key", None)

    # 2. Persist MediaGenerationJob
    job = MediaGenerationJob(
        user_id=user.id,
        org_id=org.id,
        prompt=request.prompt,
        provider=provider,
        parameters=parameters,
        status="pending",
        owner_boot_id=BOOT_ID,
        heartbeat_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 3. Dispatch Provider Task
    if provider == "mock":
        asyncio.create_task(_with_heartbeat(lambda: mock_generate_media_task(job.id), job.id))
    else:
        asyncio.create_task(
            _with_heartbeat(lambda: gemini_generate_media_task(job.id, user.id, org.id, custom_api_key=request_api_key), job.id)
        )

    return job


async def get_media_job(db: AsyncSession, user: User, job_id: str) -> Optional[MediaGenerationJob]:
    from app.services.billing_service import get_or_create_default_org
    is_admin = getattr(user, "role", "") == "admin"
    org = await get_or_create_default_org(db, user)

    stmt = select(MediaGenerationJob).where(MediaGenerationJob.id == job_id)
    if not is_admin:
        stmt = stmt.where(
            (MediaGenerationJob.user_id == user.id) | (MediaGenerationJob.org_id == org.id)
        )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    return job
