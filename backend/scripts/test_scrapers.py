import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.services.scraping.ad_library_provider import AdLibraryProvider
from app.services.scraping.adyntel_provider import AdyntelProvider

async def test_providers():
    async with async_session_maker() as db:
        print("Testing Apify...")
        ad_lib = AdLibraryProvider(db, "org_id", "user_id")
        creatives = await ad_lib._query_apify("Real madrid", "US", 10)
        print(f"Apify found: {len(creatives)}")
        
        print("Testing Adyntel...")
        adyntel = AdyntelProvider(db, "org_id", "user_id")
        adyntel_creatives = await adyntel.search("Real madrid", 10)
        print(f"Adyntel found: {len(adyntel_creatives)}")

if __name__ == "__main__":
    asyncio.run(test_providers())
