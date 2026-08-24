import asyncio
import os
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
sys.path.append(os.path.abspath('backend'))

from app.db.session import async_session_maker
from app.models.user import User
from app.services.scraping.ad_library_provider import AdLibraryProvider
from sqlalchemy import select

brands = [
    {"name": "Nike", "country": "US"},
    {"name": "Zalando", "country": "DE"},
    {"name": "Spotify", "country": "GB"},
    {"name": "Allbirds", "country": "US"},
    {"name": "ThisBrandDoesNotExist12345", "country": "US"}
]

async def run_test():
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalars().first()
        org_id = user.organization.id if hasattr(user, 'organization') and user.organization else 'org_1'
        user_id = user.id
    provider = AdLibraryProvider(None, org_id, user_id)

    print("--- BRIGHT DATA 5-BRAND TEST ---")
    
    for brand in brands:
        print(f"\nTesting: {brand['name']} ({brand['country']})")
        try:
            creatives = await provider._query_brightdata(
                brand['name'], brand['country'], max_records=15
            )
            print(f"Record count: {len(creatives)}")
            if creatives:
                c = creatives[0]
                completeness = {
                    "headline": bool(c.headline),
                    "body": bool(c.body),
                    "cta": bool(c.cta),
                    "landing_url": bool(c.landing_url),
                    "first_seen": bool(c.first_seen),
                    "spend_band": c.spend_band,
                    "impressions_est": c.impressions_est
                }
                print("Sample Field Completeness (first record):")
                for k, v in completeness.items():
                    print(f"  {k}: {v}")
                print(f"Sample Landing URL: {c.landing_url}")
            else:
                print("No creatives found.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
