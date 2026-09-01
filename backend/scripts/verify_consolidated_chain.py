import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

# Configure logging to see provider attempts
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from app.db.session import async_session_maker
from app.services.scraping.ad_library_provider import AdLibraryProvider, DISCOVERY_PROVIDER_CHAIN
from app.services import discover_service
from app.schemas.discover import SearchParams
from app.models.user import User
from sqlalchemy import select

async def main():
    print("=" * 70)
    print("TEST 1: CONSOLIDATED CHAIN CONSTANT & PROVIDER ORDER")
    print("=" * 70)
    print(f"Canonical DISCOVERY_PROVIDER_CHAIN: {DISCOVERY_PROVIDER_CHAIN}")

    async with async_session_maker() as db:
        ad_lib = AdLibraryProvider(db, "test_org", "test_user")
        print(f"Metapi Key Configured: {bool(ad_lib.metapi_provider.metapi_api_key)}")
        print(f"Adyntel Key Configured: {bool(ad_lib.adyntel_provider.adyntel_api_key)}")
        print(f"Meta Token Configured: {bool(ad_lib.meta_token)}")
        print(f"Apify Token Configured: {bool(ad_lib.apify_token)}")

        print("\n" + "=" * 70)
        print("TEST 2: DIRECT AD_LIBRARY_PROVIDER SEARCH EXECUTION")
        print("=" * 70)
        results = await ad_lib.search("shopify", max_records=5)
        print(f"\nSearch Finished!")
        print(f"Provider Used: {ad_lib.last_provider_used}")
        print(f"Sources Tried: {ad_lib.sources_tried}")
        print(f"Results Count: {len(results)}")
        if results:
            for i, r in enumerate(results[:3]):
                print(f"  #{i+1} [Format: {r.format}] Headline: '{r.headline}' | CTA: '{r.cta}' | Source: {r.data_source}")

        print("\n" + "=" * 70)
        print("TEST 3: DISCOVER_SERVICE PIPELINE CALLING CONSOLIDATED PROVIDER")
        print("=" * 70)
        admin_user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
        params = SearchParams(query="gymshark", platform="all", format="all", max_records=5)
        job = await discover_service.trigger_search(db, params, admin_user.id, None)
        print(f"Created Scrape Job ID: {job.job_id} for query 'gymshark'")

        print("Running Discover Pipeline...")
        await discover_service.run_discovery_pipeline(job.job_id, "gymshark", {})

        status = await discover_service.get_job_status(db, job.job_id)
        print(f"Job Status: {status.status} | Stage: {status.stage_label} | Records: {status.records_found}")

if __name__ == "__main__":
    asyncio.run(main())
