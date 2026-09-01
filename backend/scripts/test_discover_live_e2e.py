import asyncio
import os
import sys
import datetime

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.services import discover_service, creative_service
from app.schemas.discover import SearchParams
from app.models.user import User
from app.models.organization import Organization
from sqlalchemy import select

async def run():
    async with async_session_maker() as db:
        user_id = f"tester_{datetime.datetime.now().strftime('%H%M%S')}"
        u = User(
            id=user_id,
            email=f"{user_id}@helix.io",
            password_hash="hash",
            role="customer",
            trial_expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        )
        db.add(u)
        await db.commit()

        org = Organization(
            id=f"org_{user_id}",
            name="Live Org",
            owner_id=u.id,
            plan_id="plan_trial_default",
            credit_balance=50.0
        )
        db.add(org)
        await db.commit()

        print(f"Triggering Discover search for 'Shopify' (User: {u.email})...")
        params = SearchParams(query="Shopify", platform="all", format="all", max_records=5)
        job = await discover_service.trigger_search(db, params, u.id, None)
        print("Scrape Job Created ID:", job.job_id)

        print("Executing discovery pipeline (Metapi -> AI Scoring)...")
        await discover_service.run_discovery_pipeline(job.job_id, "Shopify", {})

        status = await discover_service.get_job_status(db, job.job_id, u.id, org.id)
        print(f"Pipeline Result -> Status: {status.status}, Progress: {status.progress}%, Records Found: {status.records_found}")

        creatives = await creative_service.get_creatives(db, page=1, page_size=10, search="Shopify")
        print(f"\nTotal Creatives in Database for query 'Shopify': {len(creatives.items)}")
        for idx, item in enumerate(creatives.items[:5]):
            print(f"  #{idx+1} Format: {item.format} | Headline: '{item.headline}' | CTA: '{item.cta}' | Score: {item.scores.composite if item.scores else '—'}")

if __name__ == "__main__":
    asyncio.run(run())
