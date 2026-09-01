import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.services.scraping.metapi_provider import MetapiProvider

async def main():
    provider = MetapiProvider()
    print("Executing fresh Metapi search for 'shopify'...")
    creatives = await provider.search("shopify", limit=10)
    
    print(f"\nReturned {len(creatives)} parsed creatives.")
    print("================================================================================")
    print("PARSED CREATIVES WITH NEW HEADLINE EXTRACTION LOGIC")
    print("================================================================================")
    
    for i, c in enumerate(creatives[:5]):
        print(f"\n[Item #{i+1}]")
        print(f"  Brand Name : {c.brand_name}")
        print(f"  Headline   : {c.headline}")
        print(f"  Body (1st 80 chars): {c.body[:80].replace(chr(10), ' ')}...")
        print(f"  Format     : {c.format}")
        print(f"  Landing URL: {c.landing_url}")

if __name__ == "__main__":
    asyncio.run(main())
