import asyncio
import os
import sys
from datetime import datetime
import httpx
from dotenv import load_dotenv

load_dotenv('.env.local')

sys.path.append(os.path.abspath('backend'))
from app.db.session import async_session_maker
from app.models.user import User
from app.services.scraping.adyntel_provider import AdyntelProvider
from sqlalchemy import select

brands = [
    {"name": "Nike", "country": "US", "domain": "nike.com"},
    {"name": "Zalando", "country": "DE", "domain": "zalando.de"},
    {"name": "Spotify", "country": "GB", "domain": "spotify.com"},
    {"name": "Allbirds", "country": "US", "domain": "allbirds.com"},
    {"name": "ThisBrandDoesNotExist12345", "country": "US", "domain": "thisbranddoesnotexist12345.com"}
]

async def run_test():
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalars().first()
        org_id = user.organization.id if hasattr(user, 'organization') and user.organization else 'org_1'
        provider = AdyntelProvider(db, org_id, user.id)

        print("--- ADYNTEL 5-BRAND TEST ---")
        print(f"Using email: {provider.email}")
        
        # Test just the first brand first to check credits
        brand = brands[0]
        print(f"\nProbing Adyntel for balance check with: {brand['domain']}")
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post("https://api.adyntel.com/facebook", json={
                    "api_key": provider.api_key,
                    "email": provider.email,
                    "company_domain": brand["domain"]
                })
                print(f"Status: {resp.status_code}")
                data = resp.json()
                print(f"Response Keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")
                if isinstance(data, dict):
                    print(f"Credits or Balance in response? " 
                          f"credits: {data.get('credits', 'N/A')}, "
                          f"balance: {data.get('balance', 'N/A')}")
        except Exception as e:
            print(f"Probe Error: {e}")
            return
            
        # Continue with full 5-brand test
        for brand in brands:
            print(f"\nTesting: {brand['name']} ({brand['domain']})")
            try:
                creatives = await provider.search(
                    brand['domain'], max_records=15
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
