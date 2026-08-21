import asyncio
import os
import uuid
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(".env.local")

from app.db.session import engine, async_session_maker
from app.models.user import User
from app.models.creative import Creative
from app.models.usage_log import UsageLog
from app.services.ai.ai_router import AIRouter
from app.services.analysis_service import generate_insight_for_creative
from sqlalchemy import text

async def main():
    print("Testing AI Router and Trial System...")
    
    # 1. Create a dummy user with active trial
    test_user_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    from app.models.scrape_job import ScrapeJob
    from app.models.organization import Organization
    
    user = User(
        id=test_user_id,
        email=f"test_{test_user_id}@example.com",
        password_hash="test",
        role="customer",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7)
    )
    
    org_id = "test-org-" + str(uuid.uuid4())
    org = Organization(
        id=org_id,
        name="Test Org",
        owner_id=test_user_id
    )
    
    job_id = "test-job-" + str(uuid.uuid4())
    test_job = ScrapeJob(
        id=job_id,
        org_id=org_id,
        status="completed",
        query="test",
        created_at=now
    )
    
    creative_id = str(uuid.uuid4())
    creative = Creative(
        id=creative_id,
        job_id=job_id,
        brand_id="test-brand",
        platform="meta",
        format="video",
        headline="Test Headline",
        body="Test Body",
        cta="Test CTA"
    )

    async with async_session_maker() as db:
        try:
            db.add(user)
            await db.flush()
            
            db.add(org)
            await db.flush()
            
            db.add(test_job)
            await db.flush()
            
            db.add(creative)
            await db.commit()
            
            # 3. Generate insight (Should use Groq since it's trial and Groq is default)
            print("Generating insight via AI Router...")
            insight = await generate_insight_for_creative(db, creative_id, user)
            print(f"Success! Insight: {insight.title} | {insight.summary} | Model: {insight.model_version}")
            
            # 4. Check usage log
            print("Checking usage logs...")
            res = await db.execute(text(f"SELECT COUNT(*) FROM usage_logs WHERE user_id = '{test_user_id}'"))
            count = res.scalar()
            print(f"Usage logs count for user: {count}")
            assert count == 1
            
            # 5. Test expired trial block
            print("Testing expired trial...")
            user.trial_expires_at = now - datetime.timedelta(days=1)
            db.add(user)
            await db.commit()
            
            try:
                await generate_insight_for_creative(db, creative_id, user)
                print("FAILED: Expired trial did not block the request.")
            except Exception as e:
                print(f"SUCCESS: Expired trial blocked the request: {e}")
                
        finally:
            # Cleanup
            print("Cleaning up test data...")
            await db.execute(text(f"DELETE FROM usage_logs WHERE user_id = '{test_user_id}'"))
            await db.execute(text(f"DELETE FROM ai_insights WHERE creative_id = '{creative_id}'"))
            await db.execute(text(f"DELETE FROM creatives WHERE id = '{creative_id}'"))
            await db.execute(text(f"DELETE FROM scrape_jobs WHERE id = '{job_id}'"))
            await db.execute(text(f"DELETE FROM organizations WHERE id = '{org_id}'"))
            await db.execute(text(f"DELETE FROM users WHERE id = '{test_user_id}'"))
            await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
