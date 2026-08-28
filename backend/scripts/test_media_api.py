import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.user import User
from app.schemas.media import MediaGenerationRequest
from app.services import media_service
from sqlalchemy import select

async def test_media_pipeline():
    async with async_session_maker() as db:
        # Find a test user or the first user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No user found in DB to test with")
            return
            
        print(f"Testing as user: {user.email}")
        
        # 1. Create a job
        request = MediaGenerationRequest(
            prompt="A cinematic shot of a red car driving through a cyberpunk city",
            provider="mock"
        )
        
        job = await media_service.create_media_job(db, user, request)
        job_id = job.id
        print(f"Job created with ID: {job_id}, status: {job.status}")
        
        # 2. Polling for completion
        print("Polling for job completion...")
        for i in range(10):
            await asyncio.sleep(1)
            
            # Use a new session to avoid caching
            async with async_session_maker() as poll_db:
                polled_job = await media_service.get_media_job(poll_db, user, job_id)
                print(f"Poll {i+1}: Status is {polled_job.status}")
                if polled_job.status == "completed":
                    print(f"Job completed! Result URL: {polled_job.result_url}")
                    return
                    
        print("Job did not complete in time")

if __name__ == "__main__":
    asyncio.run(test_media_pipeline())
