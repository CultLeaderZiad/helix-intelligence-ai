import asyncio
import os
import sys
import json
import httpx

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.core.config import settings
from app.db.session import async_session_maker
from app.services.scraping.ad_library_provider import AdLibraryProvider

async def main():
    print("=" * 80)
    print("LIVE RAW PROVIDER TEST FOR QUERY: 'mo salah'")
    print("=" * 80)
    
    metapi_key = (settings.METAPI_API_KEY or "").strip().strip('"').strip("'")
    adyntel_key = (settings.ADYNTEL_API_KEY or "").strip().strip('"').strip("'")
    adyntel_email = (settings.ADYNTEL_EMAIL or "").strip().strip('"').strip("'")
    
    # -------------------------------------------------------------------------
    # 1. METAPI RAW TEST
    # -------------------------------------------------------------------------
    print("\n--- [1] METAPI RAW CALL ---")
    headers = {
        "Authorization": f"Bearer {metapi_key}",
        "Content-Type": "application/json"
    }
    payload = {"q": "mo salah", "country": "ALL"}
    print(f"Endpoint: POST https://api.metapi.io/v1/tasks")
    print(f"Payload: {json.dumps(payload)}")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        t_resp = await client.post("https://api.metapi.io/v1/tasks", json=payload, headers=headers)
        print(f"HTTP Task Post: {t_resp.status_code}")
        print(f"Task Response: {t_resp.text}")
        if t_resp.status_code in (200, 202):
            task_id = t_resp.json().get("task_id")
            for attempt in range(25):
                await asyncio.sleep(1.5)
                s_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/status", headers=headers)
                status = s_resp.json().get("status")
                print(f"  Attempt {attempt+1} ({(attempt+1)*1.5:.1f}s): status={status}")
                if status == "succeeded":
                    break
                if status in ("failed", "error"):
                    break
            
            r_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/results", headers=headers)
            print(f"HTTP Results Get: {r_resp.status_code}")
            try:
                res_data = r_resp.json()
                items = res_data.get("data") or res_data.get("results") or (res_data if isinstance(res_data, list) else [])
                print(f"Metapi returned {len(items)} ads.")
                if items:
                    print("Sample item 1:")
                    print(json.dumps(items[0], indent=2)[:600])
                else:
                    print("Raw results data:", json.dumps(res_data, indent=2))
            except Exception as e:
                print("Error parsing Metapi JSON:", e, r_resp.text[:300])

    # -------------------------------------------------------------------------
    # 2. ADYNTEL RAW TEST
    # -------------------------------------------------------------------------
    print("\n--- [2] ADYNTEL RAW CALL ---")
    domain = "mosalah.com"
    ad_payload = {
        "api_key": adyntel_key,
        "email": adyntel_email,
        "company_domain": domain,
        "active_status": "active"
    }
    print(f"Endpoint: POST https://api.adyntel.com/facebook")
    print(f"Payload: {json.dumps(ad_payload)}")
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            resp = await client.post("https://api.adyntel.com/facebook", json=ad_payload)
            print(f"HTTP Status: {resp.status_code}")
            print(f"Raw Response: {resp.text}")
        except Exception as e:
            print("Adyntel error:", e)

    # -------------------------------------------------------------------------
    # 3. PIPELINE TEST THROUGH AdLibraryProvider
    # -------------------------------------------------------------------------
    print("\n--- [3] AD_LIBRARY_PROVIDER.SEARCH('mo salah') ---")
    async with async_session_maker() as db:
        provider = AdLibraryProvider(db, "test_org", "test_user")
        results = await provider.search("mo salah", max_records=5)
        print(f"Provider used: {provider.last_provider_used}")
        print(f"Sources tried: {provider.sources_tried}")
        print(f"Creatives returned: {len(results)}")
        for i, c in enumerate(results[:3]):
            print(f"  [{i+1}] Brand: {c.brand_name} | Headline: {c.headline} | Format: {c.format} | CTA: {c.cta}")

if __name__ == "__main__":
    asyncio.run(main())
