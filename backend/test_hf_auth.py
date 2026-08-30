import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

KEY_ID = os.getenv("HF_API_KEY_ID", "").strip().strip('"\'')
KEY_SECRET = os.getenv("HF_API_KEY_SECRET", "").strip().strip('"\'')
BASE_URL = os.getenv("HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai").rstrip("/")

async def test_auth():
    print(f"Testing Higgsfield Auth against {BASE_URL}/models")
    print(f"Key ID: {KEY_ID[:8]}... (len={len(KEY_ID)})")
    print(f"Key Secret: {KEY_SECRET[:8]}... (len={len(KEY_SECRET)})")

    headers = {
        "Authorization": f"Key {KEY_ID}:{KEY_SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        # Test 1: platform.higgsfield.ai/models
        resp = await client.get(f"{BASE_URL}/models", headers=headers, timeout=15.0)
        print(f"\nResponse status on {BASE_URL}/models: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Successfully authenticated! Models count: {len(data) if isinstance(data, list) else len(data.get('models', data.get('data', [])))}")
            print("Raw data sample:", data[:3] if isinstance(data, list) else list(data.keys()))
        else:
            print("Error response:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_auth())
