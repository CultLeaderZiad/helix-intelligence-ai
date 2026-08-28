import sys
import os
import asyncio
import time
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_session_maker
from app.models.creative import Creative
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.openrouter_provider import OpenRouterProvider
from app.services.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.core.config import settings

async def get_creatives():
    async with async_session_maker() as session:
        # Get 3 creatives that have some body text
        result = await session.execute(
            select(Creative).where(Creative.body != None).limit(3)
        )
        return result.scalars().all()

async def test_provider(name, provider, creative):
    print(f"\n[{name}] Testing creative: {creative.headline[:30]}...")
    start_time = time.time()
    try:
        insight = await provider.generate_insight(creative, context="Focus on the core hook.")
        latency = time.time() - start_time
        print(f"[{name}] SUCCESS - Latency: {latency:.2f}s")
        print(f"[{name}] Insight: {insight.title} - {insight.summary}")
        return True
    except Exception as e:
        latency = time.time() - start_time
        print(f"[{name}] FAILED - Latency: {latency:.2f}s")
        print(f"[{name}] Error: {str(e)}")
        return False

async def get_raw_openai_completion(name, base_url, api_key, model):
    print(f"\n[{name}] Fetching raw completion to check for billing headers/usage...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, say 'test'."}]
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{base_url}/chat/completions", headers=headers, json=data)
            print(f"[{name}] Status: {res.status_code}")
            print(f"[{name}] Headers (X- fields):")
            for k, v in res.headers.items():
                if k.lower().startswith("x-"):
                    print(f"  {k}: {v}")
            body = res.json()
            if "usage" in body:
                print(f"[{name}] Usage: {body['usage']}")
            if "cost" in body:
                print(f"[{name}] Cost info in body: {body['cost']}")
    except Exception as e:
        print(f"[{name}] Raw test failed: {e}")


async def main():
    if not settings.AIHUBMIX_API_KEY:
        print("ERROR: AIHUBMIX_API_KEY is not set in .env.local or environment.")
    if not settings.TOKENHARBOR_API_KEY:
        print("ERROR: TOKENHARBOR_API_KEY is not set in .env.local or environment.")
        
    creatives = await get_creatives()
    if not creatives:
        print("No creatives found in DB. Need real creatives to test.")
        return
        
    print(f"Found {len(creatives)} creatives. Starting tests...")
    
    groq = GroqProvider()
    or_prov = OpenRouterProvider(trial_mode=True)
    aihubmix = OpenAICompatibleProvider(
        base_url="https://aihubmix.com/v1",
        api_key=settings.AIHUBMIX_API_KEY,
        default_model="glm-4.7-flash-free"
    )
    tokenharbor = OpenAICompatibleProvider(
        base_url="https://tokenharbor.ai/v1",
        api_key=settings.TOKENHARBOR_API_KEY,
        default_model="qwen3.8-27b:free"
    )
    
    for i, c in enumerate(creatives):
        print(f"\n{'='*50}\nCREATIVE {i+1}: {c.headline}\n{'='*50}")
        await test_provider("Groq", groq, c)
        await test_provider("OpenRouter", or_prov, c)
        if settings.AIHUBMIX_API_KEY:
            await test_provider("AIHubMix", aihubmix, c)
        if settings.TOKENHARBOR_API_KEY:
            await test_provider("TokenHarbor", tokenharbor, c)
            
    # Check billing/raw responses
    print(f"\n{'='*50}\nRAW BILLING TESTS\n{'='*50}")
    if settings.AIHUBMIX_API_KEY:
        await get_raw_openai_completion("AIHubMix", "https://aihubmix.com/v1", settings.AIHUBMIX_API_KEY, "glm-4.7-flash-free")
    if settings.TOKENHARBOR_API_KEY:
        await get_raw_openai_completion("TokenHarbor", "https://tokenharbor.ai/v1", settings.TOKENHARBOR_API_KEY, "qwen3.8-27b:free")

if __name__ == "__main__":
    asyncio.run(main())
