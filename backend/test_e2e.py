"""
End-to-end test for Helix Intelligence backend.

This script:
1. Creates a test user and organization in the REAL database
2. Triggers a search via discover_service  
3. Fetches the job back and verifies data round-trips
4. ALWAYS cleans up test data, even on failure

BRANCH SAFETY:
- Uses DATABASE_URL from .env.local (which should point to the `dev` branch)
- Prints the target DB URL at startup so you can verify
- Does NOT hardcode any production URLs
"""
import asyncio
import os
import sys
import uuid

# Ensure backend root is in python path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.schemas.discover import SearchParams
from app.services.discover_service import trigger_search, get_job_status


async def main():
    # Force disable mocks for this test
    settings.USE_MOCKS = False
    
    db_url = settings.async_database_url
    print(f"Using DB: {db_url[:60]}...")
    
    # Safety check: warn if URL doesn't look like a dev branch
    if "dev" not in os.getenv("NEON_BRANCH", "") and "dev" not in db_url:
        print("WARNING: NEON_BRANCH is not 'dev'. Are you sure you're targeting the dev branch?")
    
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    job_id = None
    success = False
    
    try:
        async with async_session() as db:
            # Create test user
            user = User(
                id=user_id,
                email=f"test_{user_id}@example.com",
                password_hash="testhash",
                role="admin"
            )
            db.add(user)
            await db.flush()
            
            # Create test organization
            org = Organization(
                id=org_id,
                name="Test E2E Org",
                owner_id=user_id,
                plan="free"
            )
            db.add(org)
            await db.commit()
            print(f"Created user: {user.email}")
            print(f"Created org: {org.name}")
            
            # Test ScrapeJob creation and fetching via discover_service
            search_params = SearchParams(query="Test Competitor Query")
            job_init = await trigger_search(db, search_params, user_id)
            job_id = job_init.job_id
            print(f"\nTriggered Job (from trigger_search):")
            print(f" - ID: {job_init.job_id}")
            print(f" - Status: {job_init.status}")
            print(f" - Stage Label: {job_init.stage_label}")
            
            job_fetched = await get_job_status(db, job_init.job_id)
            print(f"\nFetched Job (from get_job_status):")
            print(f" - ID: {job_fetched.job_id}")
            print(f" - Status: {job_fetched.status}")
            print(f" - Stage Label: {job_fetched.stage_label}")
            
            if job_init.job_id == job_fetched.job_id:
                print("\nSUCCESS: Data round-tripped correctly to Neon!")
                success = True
            else:
                print("\nERROR: Job IDs did not match!")

    except Exception as e:
        print(f"\nError occurred during test: {e}")
    
    finally:
        # ALWAYS clean up, even on error
        print("\nCleaning up test data...")
        try:
            async with async_session() as db:
                if job_id:
                    await db.execute(
                        sqlalchemy_delete(ScrapeJob).where(ScrapeJob.id == job_id)
                    )
                await db.execute(
                    sqlalchemy_delete(Organization).where(Organization.id == org_id)
                )
                await db.execute(
                    sqlalchemy_delete(User).where(User.id == user_id)
                )
                await db.commit()
                print("Cleanup complete.")
        except Exception as cleanup_err:
            print(f"Cleanup error (may need manual cleanup): {cleanup_err}")
        
        await engine.dispose()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
