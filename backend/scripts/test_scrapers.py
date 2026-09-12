import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.services.scraping.metapi_provider import MetapiProvider

async def test_providers():
    async with async_session_maker() as db:
        print("Testing Metapi...")
        metapi = MetapiProvider(db, "org_id", "user_id")
        metapi_creatives = await metapi.search("shopify", 10)
        print(f"Metapi found: {len(metapi_creatives)}")
        if metapi_creatives:
            print(f"Sample Metapi creative format: {metapi_creatives[0].format}")
            print(f"Sample Metapi creative headline: {metapi_creatives[0].headline}")
            print(f"Sample Metapi creative landing_url: {metapi_creatives[0].landing_url}")
            print(f"Sample Metapi creative cta: {metapi_creatives[0].cta}")

if __name__ == "__main__":
    asyncio.run(test_providers())
