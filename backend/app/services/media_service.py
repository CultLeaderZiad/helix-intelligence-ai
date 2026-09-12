import asyncio
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
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
from app.services.media.higgsfield_provider import HiggsfieldProvider
from app.services.media.higgsfield_registry import resolve_mode_spec
from app.core.config import settings
from app.core.security import sign_job_webhook_token

logger = logging.getLogger(__name__)

async def _reread_status(db: AsyncSession, job: MediaGenerationJob) -> str:
    """Current persisted status, or the in-memory one if the DB is unreachable.

    Used on the failure paths, where the session may be the thing that just
    broke: a cancellation must never turn into a second, louder exception that
    hides the original error.
    """
    try:
        await db.refresh(job)
    except Exception:  # pragma: no cover - defensive
        return str(job.status or "")
    return str(job.status or "")


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

        if job.status in TERMINAL_STATUSES:
            # Canceled (or settled) between dispatch of this task and now.
            logger.info("Gemini job %s is already %s; skipping generation", job_id, job.status)
            return

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

            # The user may have cancelled while the provider was working. A
            # cancelled job stays cancelled and is never charged.
            await db.refresh(job)
            if job.status == "canceled":
                logger.info("Gemini job %s finished after cancellation; result discarded, no usage recorded", job_id)
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
            logger.error("Gemini image generation failed for job %s: %s", job_id, str(e))
            if await _reread_status(db, job) == "canceled":
                return
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


async def higgsfield_generate_media_task(job_id: str):
    from app.db.session import async_session_maker
    provider = HiggsfieldProvider()

    async with async_session_maker() as db:
        result = await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        try:
            logger.info("Starting Higgsfield generation for job %s", job_id)
            # The callback URL carries a token derived from this job's id and
            # SECRET_KEY, so a delivery can only ever update the job it belongs
            # to (see webhooks router). Without it the endpoint had to trust any
            # anonymous POST that knew a provider_job_id.
            webhook_url = (
                f"{settings.PUBLIC_API_BASE_URL}/webhooks/higgsfield"
                f"?token={sign_job_webhook_token(job.id)}"
            )
            params = job.parameters or {}

            request_id = await provider.generate_media(
                job.prompt,
                params,
                webhook_url=webhook_url
            )

            job.provider_job_id = request_id
            job.status = "in_progress"
            await db.commit()

            # Polling fallback
            for _ in range(60):
                await asyncio.sleep(2.0)
                await db.refresh(job)
                if job.status in ["completed", "failed", "nsfw", "canceled"]:
                    return

                status_info = await provider.check_status(request_id)
                status = status_info.get("status")

                if status == "completed":
                    await db.refresh(job)
                    if job.status == "canceled":
                        logger.info("Higgsfield job %s completed after cancellation; result discarded", job_id)
                        return
                    job.status = "completed"
                    result_url = status_info.get("url")
                    if result_url:
                        job.result_url = result_url
                    await db.commit()
                    return
                elif status in ["failed", "nsfw"]:
                    await db.refresh(job)
                    if job.status == "canceled":
                        return
                    job.status = "failed"
                    job.error_message = f"Higgsfield status: {status}"
                    await db.commit()
                    return

            if await _reread_status(db, job) != "canceled":
                job.status = "failed"
                job.error_message = "Polling timed out"
                await db.commit()

        except Exception as e:
            logger.error("Error in Higgsfield generation task: %s", e)
            if await _reread_status(db, job) == "canceled":
                return
            job.status = "failed"
            err_text = str(e)
            if "401" in err_text or "Unauthorized" in err_text:
                job.error_message = (
                    "Higgsfield rejected the API credentials (401). "
                    "This has been logged for the team — please retry later."
                )
            elif "403" in err_text or "Forbidden" in err_text:
                job.error_message = (
                    "Higgsfield denied this request (403). "
                    "This has been logged for the team — please retry later."
                )
            else:
                job.error_message = err_text[:200]
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
    is_admin = getattr(user, "role", None) == "admin"
    is_trial = not is_admin and ((plan.type == "trial") or (getattr(org, "plan", "") == "trial") or bool(getattr(org, "plan_id", "").startswith("plan_trial")))

    # Tiered Routing:
    # - Trial Users -> Gemini
    # - Paid Users / Admins -> Higgsfield (or requested BYOK/custom provider)
    if is_trial:
        provider = "gemini"
    elif requested_provider == "gemini":
        provider = "gemini"
    elif requested_provider in ("higgsfield", "default", ""):
        provider = "higgsfield"
    elif requested_provider == "mock" and not settings.USE_MOCKS:
        provider = "higgsfield"
    else:
        provider = requested_provider or "higgsfield"

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
    if provider == "higgsfield":
        asyncio.create_task(higgsfield_generate_media_task(job.id))
    elif provider == "mock":
        asyncio.create_task(mock_generate_media_task(job.id))
    else:
        asyncio.create_task(gemini_generate_media_task(job.id, user.id, org.id))

    return job


# Statuses a user may still cancel. Anything past these is already settled and
# cancelling would be a lie.
CANCELLABLE_STATUSES = {"pending", "queued", "running", "in_progress", "processing"}
TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}


async def get_media_job(db: AsyncSession, user: User, job_id: str) -> Optional[MediaGenerationJob]:
    """Owner-scoped job read.

    A job id is not a capability: every other read in the app is scoped to the
    caller's account or workspace, and this one used to filter on `id` alone,
    which let any signed-in user pull another user's prompt, result URL and
    error text by iterating ids. Same-owner OR same-workspace is the rule; the
    org comes from the same helper the write path uses so team members keep
    seeing their shared jobs.
    """
    org = await get_or_create_default_org(db, user, lock_row=False)
    conditions = [MediaGenerationJob.user_id == user.id]
    if org is not None:
        conditions.append(MediaGenerationJob.org_id == org.id)
    result = await db.execute(
        select(MediaGenerationJob).where(
            MediaGenerationJob.id == job_id,
            or_(*conditions),
        )
    )
    return result.scalar_one_or_none()


async def cancel_media_job(db: AsyncSession, user: User, job_id: str) -> dict:
    """Cancel a generation that has not produced a result yet.

    Returns an explicit outcome instead of a blanket success:

    * ``canceled``            — status flipped; the queued provider task
      checks for this before it spends a generation and before it records
      usage, so the attempt is never billed.
    * ``already_terminal``    — nothing to cancel; the caller gets the real
      status rather than a fake "we cancelled it".
    * ``not_found``           — wrong id or not yours (the router renders both
      as 404 so this endpoint cannot be used to probe other accounts).

    A provider that is already mid-request cannot be recalled over our
    transport, so the message says "canceled locally, an in-flight provider
    call may still finish and its result will be discarded" rather than
    promising an abort we do not have.
    """
    job = await get_media_job(db, user, job_id)
    if not job:
        return {"outcome": "not_found", "job_id": job_id}

    if job.status not in CANCELLABLE_STATUSES:
        return {
            "outcome": "already_terminal",
            "job_id": job_id,
            "status": job.status,
            "message": f"This job is already {job.status}, so there is nothing to cancel.",
        }

    provider = job.provider
    job.status = "canceled"
    job.error_message = "Canceled by user."
    await db.commit()
    logger.info("Media job %s canceled by user %s (provider=%s)", job_id, user.id, provider)

    detail = "Job canceled. Credits for this attempt were not charged."
    if provider == "higgsfield":
        detail = (
            "Job canceled. The provider may still finish the request on its side; "
            "its result will be discarded and nothing is charged."
        )
    return {"outcome": "canceled", "job_id": job_id, "status": "canceled", "message": detail}
