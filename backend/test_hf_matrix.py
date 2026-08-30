import asyncio
import httpx
import os
import base64
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

KEY_ID = os.getenv("HF_API_KEY_ID", "").strip().strip('"\'')
KEY_SECRET = os.getenv("HF_API_KEY_SECRET", "").strip().strip('"\'')

basic_token = base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()

async def test_matrix():
    urls = [
        "https://platform.higgsfield.ai/models",
        "https://platform.higgsfield.ai/v1/models",
        "https://api.higgsfield.ai/models",
        "https://api.higgsfield.ai/v1/models",
        "https://platform.higgsfield.ai/higgsfield-ai/models",
    ]

    header_variants = [
        ("Key format", {"Authorization": f"Key {KEY_ID}:{KEY_SECRET}"}),
        ("Bearer Key:Secret", {"Authorization": f"Bearer {KEY_ID}:{KEY_SECRET}"}),
        ("Bearer Secret only", {"Authorization": f"Bearer {KEY_SECRET}"}),
        ("Bearer ID only", {"Authorization": f"Bearer {KEY_ID}"}),
        ("Basic Auth", {"Authorization": f"Basic {basic_token}"}),
        ("hf-api-key headers", {"hf-api-key": KEY_ID, "hf-secret": KEY_SECRET}),
        ("X-API-Key Key:Secret", {"X-API-Key": f"{KEY_ID}:{KEY_SECRET}"}),
        ("X-API-Key Secret only", {"X-API-Key": KEY_SECRET}),
        ("X-API-Key ID only", {"X-API-Key": KEY_ID}),
    ]

    async with httpx.AsyncClient() as client:
        for url in urls:
            print(f"\n================ Target URL: {url} ================")
            for name, hdrs in header_variants:
                hdrs = {**hdrs, "Accept": "application/json"}
                try:
                    resp = await client.get(url, headers=hdrs, timeout=6.0)
                    print(f"[{resp.status_code}] {name:25} -> {resp.text[:100]}")
                except Exception as e:
                    print(f"[ERR] {name:25} -> {e}")

if __name__ == "__main__":
    asyncio.run(test_matrix())
