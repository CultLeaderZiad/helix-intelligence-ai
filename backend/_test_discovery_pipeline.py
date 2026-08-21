import asyncio
from app.db.session import async_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.organization import Organization
from app.services.discover_service import trigger_search
from app.schemas.discover import SearchParams
import datetime
import uuid

async def test_discovery():
    print("Testing Discovery Pipeline...")
    
    async with async_session_maker() as db:
        # Get an existing org or create a test one
        from sqlalchemy import select
        result = await db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if not org:
            print("No organization found. Creating a test org...")
            org = Organization(
                id=str(uuid.uuid4()),
                name="Test Org",
                owner_id="test-user"
            )
            db.add(org)
            await db.commit()
            
        print(f"Using Organization: {org.id}")
        user_id = org.owner_id
        
    print("Triggering search for 'Nike Running'...")
    search_params = SearchParams(query="Nike Running")
    
    # We will invoke run_discovery_pipeline directly instead of background tasks 
    # so we can await it sequentially in this test script
    from app.services.discover_service import run_discovery_pipeline
    
    # But trigger_search creates the DB entry. We'll pass None for background tasks
    async with async_session_maker() as db:
        job = await trigger_search(db, search_params, user_id, background_tasks=None)
    print(f"Created ScrapeJob: {job.job_id}")
    
    print("Running pipeline manually in foreground for testing...")
    await run_discovery_pipeline(job.job_id, search_params.query)
    print("Pipeline finished.")
    
    print("Verifying database records...")
    async with async_session_maker() as db:
        # Check Job
        from sqlalchemy import select
        job_result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job.job_id))
        final_job = job_result.scalar_one()
        print(f"Job Status: {final_job.status}, Stage: {final_job.stage_label}, Error: {final_job.error_msg}")
        print(f"Creatives Extracted: {final_job.record_count}")
        
        # Check Creatives
        from app.models.creative import Creative
        from app.models.creative_score import CreativeScore
        creatives_result = await db.execute(select(Creative).where(Creative.job_id == job.job_id))
        creatives = creatives_result.scalars().all()
        for c in creatives:
            print(f" - Creative [{c.platform}]: {c.headline} | {c.body[:30]}... | {c.cta}")
            
        # Check generated patterns
        # AI generated patterns are linked to creatives or the brand/org
        # Let's just check how many patterns exist for this org now.
        from app.models.pattern import Pattern
        patterns_result = await db.execute(select(Pattern).where(Pattern.job_id == job.job_id))
        patterns = patterns_result.scalars().all()
        print(f"Total Patterns for Org: {len(patterns)}")

if __name__ == "__main__":
    asyncio.run(test_discovery())
