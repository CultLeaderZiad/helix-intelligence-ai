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

async def main():
    api_key = settings.METAPI_API_KEY.strip().strip('"').strip("'")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "q": "gymshark",
        "country": "ALL"
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        task_resp = await client.post("https://api.metapi.io/v1/tasks", json=payload, headers=headers)
        task_data = task_resp.json()
        task_id = task_data.get("task_id")
        
        for _ in range(25):
            await asyncio.sleep(1.5)
            status_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/status", headers=headers)
            if status_resp.json().get("status") == "succeeded":
                break
                
        results_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/results", headers=headers)
        results_data = results_resp.json()
        
        with open("backend/scripts/raw_metapi_gymshark.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        print("Saved raw_metapi_gymshark.json successfully!")

if __name__ == "__main__":
    asyncio.run(main())
