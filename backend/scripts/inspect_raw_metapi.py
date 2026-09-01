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

async def query_metapi_raw(query: str, limit: int = 3):
    api_key = settings.METAPI_API_KEY.strip().strip('"').strip("'")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "country": "ALL"
    }
    
    print(f"\n=======================================================")
    print(f"QUERYING METAPI RAW: '{query}'")
    print(f"Payload sent: {json.dumps(payload)}")
    print(f"=======================================================")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        task_resp = await client.post("https://api.metapi.io/v1/tasks", json=payload, headers=headers)
        print(f"Task creation HTTP status: {task_resp.status_code}")
        if task_resp.status_code not in (200, 202):
            print("Task creation body:", task_resp.text)
            return None
            
        task_data = task_resp.json()
        task_id = task_data.get("task_id")
        print(f"Task ID received: {task_id}")
        
        for attempt in range(25):
            await asyncio.sleep(1.5)
            status_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/status", headers=headers)
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"[{attempt*1.5:.1f}s] Task status: {status}")
            if status == "succeeded":
                break
            if status in ("failed", "error"):
                print("Task failed:", status_data)
                return None
                
        results_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/results", headers=headers)
        print(f"Results HTTP status: {results_resp.status_code}")
        results_data = results_resp.json()
        
        # Save raw JSON to disk for full inspection
        filename = f"backend/scripts/raw_metapi_{query.replace(' ', '_').lower()}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        print(f"Saved full raw JSON to: {filename}")
        
        # Print first 2-3 items in detail
        items = results_data.get("data") or results_data.get("results") or results_data if isinstance(results_data, list) else []
        if isinstance(results_data, dict):
            print("Top level keys:", list(results_data.keys()))
            if "total" in results_data:
                print("Total count in response:", results_data.get("total"))
            items = results_data.get("data") or results_data.get("results") or []

        print(f"\nTotal items returned: {len(items)}")
        for idx, item in enumerate(items[:limit]):
            print(f"\n--- RAW ITEM #{idx+1} ---")
            print(json.dumps(item, indent=2, ensure_ascii=False))

async def main():
    # 1. Inspect "Shopify"
    await query_metapi_raw("shopify", limit=2)
    
    # 2. Inspect unambiguous brand: "Gymshark"
    await query_metapi_raw("gymshark", limit=2)

if __name__ == "__main__":
    asyncio.run(main())
