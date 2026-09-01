import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.usage_log import UsageLog
from app.services.discover_service import trigger_search
from app.schemas.discover import SearchParams
from sqlalchemy import select

async def run_dynamic_queries():
    # Pick completely un-tested, arbitrary queries
    dynamic_queries = [
        "duolingo",
        "airbnb",
    ]

    print("=" * 60)
    print("DEMONSTRATING DYNAMIC SEARCH PIPELINE FOR ARBITRARY USER QUERIES")
    print("=" * 60)

    for q in dynamic_queries:
        print(f"\n>>> Running live search for: '{q}'")
        async with async_session_maker() as db:
            user = (await db.execute(select(User).limit(1))).scalar_one()
            org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
            if not org:
                org = (await db.execute(select(Organization).limit(1))).scalar_one()

            org.daily_credits_used_today = 0.0
            org.credit_balance = 50.0
            await db.commit()

            user_id = str(user.id)
            params = SearchParams(query=q, country="US")
            job_schema = await trigger_search(db, params, user_id, background_tasks=None)
            job_id = job_schema.job_id if hasattr(job_schema, "job_id") else job_schema.id

        # Poll for completion
        for _ in range(40):
            await asyncio.sleep(2)
            async with async_session_maker() as db:
                job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
                if job.status in ("succeeded", "failed"):
                    break

        async with async_session_maker() as db:
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            creatives = (await db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()

            print(f"Result for '{q}':")
            print(f"  Status: {job.status} | Stage: {job.stage} | Label: {job.stage_label}")
            print(f"  Live Records Scraped: {len(creatives)}")
            for idx, c in enumerate(creatives[:2]):
                print(f"  Ad #{idx+1}:")
                print(f"    Headline: {repr(c.headline)}")
                print(f"    Body: {repr(c.body[:90] if c.body else '')}...")
                print(f"    Format: {c.format}, CTA: {c.cta}")
                print(f"    Landing Domain: {c.landing_domain}")

if __name__ == "__main__":
    asyncio.run(run_dynamic_queries())
