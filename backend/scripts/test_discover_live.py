import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.services import discover_service
from app.schemas.discover import SearchParams
from app.models.user import User
from sqlalchemy import select

async def run():
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
        print(f"Triggering Discover search for 'shopify' (User: {user.email})...")
        params = SearchParams(query="shopify", platform="all", format="all", max_records=10)
        job = await discover_service.trigger_search(db, params, user.id, None)
        print("Scrape Job Created ID:", job.job_id)

        # Directly run background scraping pipeline
        print("Executing discovery pipeline with Metapi...")
        await discover_service.run_discovery_pipeline(job.job_id, "shopify", {})

        results = await discover_service.get_job_results(db, job.job_id, user.id, 1, 10)
        print(f"\nResults Retrieved: Total {results.total} creatives (page 1 has {len(results.items)})")
        if results.items:
            for idx, item in enumerate(results.items[:5]):
                print(f"  #{idx+1} Brand: '{item.brand_name}' | Format: {item.format} | Headline: '{item.headline}' | CTA: '{item.cta}'")

if __name__ == "__main__":
    asyncio.run(run())
