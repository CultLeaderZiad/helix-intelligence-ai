"""Diagnose Resend retrieve 401. Prints status and body only, never the key."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from app.core.config import settings

EMAIL_ID = os.getenv("RESEND_EMAIL_ID", "7de85803-7e42-4b2b-a173-07064d07df47")
key = settings.RESEND_API_KEY or ""


async def main():
    print("key_len:", len(key))
    print("key_prefix_ok:", key.startswith("re_"))
    print("key_has_quotes:", '"' in key or "'" in key)
    print("key_has_whitespace:", key != key.strip())
    headers = {"Authorization": f"Bearer {key.strip()}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        get_one = await client.get(f"https://api.resend.com/emails/{EMAIL_ID}", headers=headers)
        print("GET /emails/{id} status:", get_one.status_code)
        print("GET /emails/{id} body:", get_one.text[:300])
        listed = await client.get("https://api.resend.com/emails", headers=headers)
        print("GET /emails status:", listed.status_code)
        print("GET /emails body:", listed.text[:300])


asyncio.run(main())
