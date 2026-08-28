import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.user import User
from app.models.media_job import MediaGenerationJob
from app.models.webhook_event import WebhookEvent
from app.schemas.media import MediaGenerationRequest
from app.services.media.higgsfield_provider import HiggsfieldProvider
from app.services.media_service import create_media_job, higgsfield_generate_media_task
from app.core.config import settings


from app.models.organization import Organization

async def setup_test_user():
    user_email = "test_media_user@example.com"
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == user_email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=user_email, password_hash="hashed")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user


async def cleanup_test_data(user):
    async with async_session_maker() as db:
        await db.execute(delete(MediaGenerationJob).where(MediaGenerationJob.user_id == user.id))
        await db.execute(delete(Organization).where(Organization.owner_id == user.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.execute(delete(WebhookEvent).where(WebhookEvent.request_id.like("test_req_%")))
        await db.commit()


async def test_provider_selection_and_request_creation_mocked(user):
    print("Running test: test_provider_selection_and_request_creation_mocked")
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "test_req_123"}
        mock_post.return_value = mock_response

        request = MediaGenerationRequest(
            prompt="A futuristic cityscape",
            provider="higgsfield",
            parameters={"capability": "IMAGE_FAST"}
        )
        
        async with async_session_maker() as db:
            with patch("app.services.media.higgsfield_provider.HiggsfieldProvider.check_status", new_callable=AsyncMock) as mock_status:
                mock_status.return_value = {"status": "completed", "url": "http://test/video.mp4"}
                with patch("app.services.storage_service.store_media_from_url", new_callable=AsyncMock):
                    job = await create_media_job(db, user, request)
                    
                    assert job.id is not None
                    assert job.status == "pending"
                    assert job.provider == "higgsfield"
                    
                    # Wait for background task
                    for _ in range(40):
                        await db.refresh(job)
                        if job.status == "completed":
                            break
                        await asyncio.sleep(0.1)
                    
            await db.refresh(job)
            
            assert job.provider_job_id == "test_req_123"
            assert job.status == "completed"
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://platform.higgsfield.ai/v1/text2image/soul"
            assert "params" in kwargs["json"]
            assert "prompt" in kwargs["json"]["params"]
            assert "webhook" in kwargs["json"]
    print("Passed.")


async def test_invalid_model_mocked(user):
    print("Running test: test_invalid_model_mocked")
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = Exception("HTTP 400")
        mock_post.return_value = mock_response

        request = MediaGenerationRequest(
            prompt="A futuristic cityscape",
            provider="higgsfield",
            parameters={"capability": "INVALID_MODEL"}
        )
        
        async with async_session_maker() as db:
            job = await create_media_job(db, user, request)
            for _ in range(20):
                await db.refresh(job)
                if job.status == "failed":
                    break
                await asyncio.sleep(0.1)
            await db.refresh(job)
            
            assert job.status == "failed"
            assert job.error_message is not None
    print("Passed.")


async def test_webhook_completed_mocked(user: User):
    print("Running test: test_webhook_completed_mocked")
    
    async with async_session_maker() as db:
        from app.services.billing_service import get_or_create_default_org
        org = await get_or_create_default_org(db, user)
        
        # We don't need a real task, just a job in the DB
        job_id = str(uuid.uuid4())
        job = MediaGenerationJob(
            id=job_id,
            user_id=user.id,
            org_id=org.id,
            status="in_progress",
            prompt="test webhook",
            provider="higgsfield",
            provider_job_id="test_req_webhook"
        )
    
        db.add(job)
        await db.commit()
        
        event1 = WebhookEvent(
            provider="higgsfield",
            request_id="test_req_webhook",
            status="completed",
            payload={"images": [{"url": "http://test/completed.png"}]}
        )
        db.add(event1)
        await db.commit()
        
        job.status = "completed"
        job.result_url = "http://test/completed.png"
        await db.commit()
        
        result = await db.execute(select(WebhookEvent).where(
            WebhookEvent.request_id == "test_req_webhook",
            WebhookEvent.status == "completed"
        ))
        existing_event = result.scalar_one_or_none()
        
        assert existing_event is not None
    print("Passed.")


async def test_live_smoke_test():
    if os.environ.get("RUN_LIVE_TESTS", "false").lower() != "true":
        print("Skipping test_live_smoke_test (RUN_LIVE_TESTS != true)")
        return
        
    print("Running test: test_live_smoke_test")
    assert settings.HF_API_KEY_ID, "API ID is missing"
    assert settings.HF_API_KEY_SECRET, "API Secret is missing"
    
    provider = HiggsfieldProvider()
    params = {"resolution": "1024x1024", "quality": "720p"}
    
    request_id = await provider.generate_media("A minimalist white cube on a black background", params)
    assert request_id is not None
    
    for _ in range(30):
        await asyncio.sleep(2.0)
        status_info = await provider.check_status(request_id)
        status = status_info.get("status")
        
        if status == "completed":
            assert "url" in status_info
            print("Passed.")
            return
        elif status in ["failed", "nsfw"]:
            assert False, f"Live generation failed with status: {status}"
            
    assert False, "Live generation timed out"


async def main():
    user = await setup_test_user()
    try:
        await test_provider_selection_and_request_creation_mocked(user)
        await test_invalid_model_mocked(user)
        await test_webhook_completed_mocked(user)
        await test_live_smoke_test()
    finally:
        await cleanup_test_data(user)
    print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
