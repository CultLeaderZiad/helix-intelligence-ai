import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.services.scraping.ad_library_provider import AdLibraryProvider
from app.services.scraping.adyntel_provider import AdyntelProvider
from app.services.scraping.metapi_provider import MetapiProvider

async def test_providers():
    async with async_session_maker() as db:
        print("Testing Apify...")
        ad_lib = AdLibraryProvider(db, "org_id", "user_id")
        creatives = await ad_lib.query_apify("Real madrid", "US", 10)
        print(f"Apify found: {len(creatives)}")
        
        print("Testing Adyntel...")
        adyntel = AdyntelProvider(db, "org_id", "user_id")
        adyntel_creatives = await adyntel.search("Real madrid", 10)
        print(f"Adyntel found: {len(adyntel_creatives)}")

        print("\nTesting Metapi...")
        metapi = MetapiProvider(db, "org_id", "user_id")
        metapi.metapi_api_key = "mk_live_cbd9917f030533d6a1bfe1d0897e900a002afef704458c459010271359c5f0e7"
        metapi_creatives = await metapi.search("shopify", 10)
        print(f"Metapi found: {len(metapi_creatives)}")
        if metapi_creatives:
            print(f"Sample Metapi creative format: {metapi_creatives[0].format}")
            print(f"Sample Metapi creative headline: {metapi_creatives[0].headline}")
            print(f"Sample Metapi creative landing_url: {metapi_creatives[0].landing_url}")
            print(f"Sample Metapi creative cta: {metapi_creatives[0].cta}")

if __name__ == "__main__":
    asyncio.run(test_providers())
