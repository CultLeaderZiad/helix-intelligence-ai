import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.services.discover_service import run_discovery_pipeline
from app.models.scrape_job import ScrapeJob
from sqlalchemy import select

async def test_pipeline():
    # Pick the most recent job
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(1))
        job = result.scalar_one_or_none()
        if not job:
            print("No job found")
            return
        job_id = job.id
        print(f"Testing pipeline for job {job_id}")

    try:
        await run_discovery_pipeline(job_id, "Real madrid", {})
        print("Pipeline finished.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
