import asyncio
import os
from unittest.mock import patch
import httpx
from dotenv import load_dotenv

# Load .env.local
load_dotenv(".env.local")

# Print keys present in .env.local
print("--- ENVIRONMENT VARIABLES LOADED (.env.local) ---")
expected_keys = [
    "GROQ_API_KEY",
    "BRIGHTDATA_API_KEY",
    "APIFY_API_TOKEN",
    "APIFY_TOKEN",
    "META_ACCESS_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY"
]
for key in expected_keys:
    val = os.getenv(key)
    if val and len(val) > 0:
        print(f"[OK] {key} is PRESENT and NON-EMPTY")
    else:
        print(f"[MISSING] {key} is MISSING or EMPTY")
print("-" * 50)

# Import the provider
from app.services.scraping.ad_library_provider import AdLibraryProvider

def mask_headers(headers):
    masked = {}
    for k, v in headers.items():
        if k.lower() in ("authorization", "x-api-key"):
            masked[k] = "MASKED_KEY"
        else:
            masked[k] = v
    return masked

def mask_params(params):
    masked = {}
    for k, v in params.items():
        if k.lower() in ("access_token", "token", "key"):
            masked[k] = "MASKED_KEY"
        else:
            masked[k] = v
    return masked

def mask_url(url):
    import urllib.parse
    parsed = urllib.parse.urlparse(str(url))
    qs = urllib.parse.parse_qs(parsed.query)
    for k in qs:
        if k.lower() in ("access_token", "token", "key"):
            qs[k] = ["MASKED_KEY"]
    new_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))

# We will intercept the HTTPX request method using a mock client wrapper
original_client = httpx.AsyncClient

class InterceptedClient(original_client):
    async def request(self, method, url, *args, **kwargs):
        masked_url = mask_url(url)
        print(f"\n[{method}] {masked_url}")
        
        if "params" in kwargs and kwargs["params"]:
            print(f"Params: {mask_params(kwargs['params'])}")
            
        if "headers" in kwargs and kwargs["headers"]:
            print(f"Headers: {mask_headers(kwargs['headers'])}")
            
        if "json" in kwargs and kwargs["json"]:
            print(f"JSON Body: {kwargs['json']}")
            
        try:
            resp = await super().request(method, url, *args, **kwargs)
            print(f"Status Code: {resp.status_code}")
            print(f"Response Body (Raw): {resp.text[:1000]}... [truncated if long]")
            return resp
        except Exception as e:
            print(f"Request failed with Exception: {e}")
            raise e

async def run_diagnostic():
    print("\n--- STARTING DISCOVER SEARCH DIAGNOSTIC ---")
    provider = AdLibraryProvider()
    
    # Check what is configured
    print(f"\nProvider Config:")
    print(f"Meta Token Present: {bool(provider.meta_token)}")
    print(f"Bright Data Key Present: {bool(provider.brightdata_key)}")
    print(f"Apify Token Present: {bool(provider.apify_token)}")
    
    with patch('httpx.AsyncClient', new=InterceptedClient):
        filters = {"country": "US"}
        print(f"\nRunning search(query='Nike', filters={filters})")
        
        # Override the return of _query_meta_api to force it to fail if we want to see the fallback chain
        # Actually the instructions say: "show me the RAW, unparsed HTTP response from EVERY source in the ScraperProvider chain that gets attempted... Whether each one was actually called at all, or skipped (and why...)"
        # So I will just let it run naturally, but to ensure we see the chain, wait! The provider STOPS if one succeeds.
        # If the user wants to see EVERY source, I should let it run. But wait, if Meta succeeds, BrightData isn't called.
        # "that gets attempted" -> so if Meta succeeds, BrightData is skipped because Meta succeeded. This is exactly what the user wants to see!
        
        creatives = await provider.search("Nike", filters=filters)
        print(f"\nSearch complete. Found {len(creatives)} creatives.")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
