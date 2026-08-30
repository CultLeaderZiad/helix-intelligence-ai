import asyncio
import httpx
import time
from app.core.config import settings

async def test_higgsfield_generation():
    raw_key_id = getattr(settings, "HF_API_KEY_ID", "") or ""
    raw_key_secret = getattr(settings, "HF_API_KEY_SECRET", "") or ""
    key_id = raw_key_id.strip().strip('"\'')
    key_secret = raw_key_secret.strip().strip('"\'')

    if not key_id or not key_secret:
        print("ERROR: HF_API_KEY_ID or HF_API_KEY_SECRET not set in .env.local")
        return

    print(f"Testing Higgsfield with HF_API_KEY_ID: {key_id[:6]}... (length: {len(key_id)})")
    
    headers = {
        "Authorization": f"Key {key_id}:{key_secret}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Official Soul v2 endpoint (https://docs.higgsfield.ai/docs/quickstart)
    url = "https://api.higgsfield.ai/higgsfield-ai/soul/v2/standard"
    
    payload = {
        "prompt": "A futuristic luxury electric sports car driving on a coastal road at sunset, cinematic lighting, photorealistic 8k",
        "aspect_ratio": "1:1",
        "quality": "standard"
    }
    
    start_time = time.time()
    print(f"Starting generation request to {url}...")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            if resp.status_code >= 400:
                print(f"API Error: HTTP {resp.status_code} - {resp.text}")
                return
            data = resp.json()
        except Exception as e:
            print(f"Request Error: {e}")
            return
            
        print("Generation job queued:", data)
        request_id = data.get("request_id")
        
        if not request_id:
            print("No request_id returned in response")
            return
            
        # Polling status
        polling_url = f"https://api.higgsfield.ai/requests/{request_id}/status"
        
        while True:
            await asyncio.sleep(3.0)
            print(f"Polling {polling_url}...")
            
            try:
                poll_resp = await client.get(polling_url, headers=headers, timeout=15.0)
                if poll_resp.status_code >= 400:
                    print(f"Polling HTTP Error: {poll_resp.status_code} - {poll_resp.text}")
                    return
                poll_data = poll_resp.json()
                
                status = poll_data.get("status")
                print(f"Status: {status}")
                
                if status in ["completed", "failed", "nsfw"]:
                    latency = time.time() - start_time
                    print(f"\nFinished with status: {status}")
                    print(f"Latency: {latency:.2f} seconds")
                    
                    if status == "completed":
                        images = poll_data.get("images", [])
                        if images and isinstance(images, list):
                            print(f"Media URL: {images[0].get('url')}")
                        elif poll_data.get("payload", {}).get("images"):
                            print(f"Media URL: {poll_data['payload']['images'][0].get('url')}")
                    print(f"Full response: {poll_data}")
                    break
                    
            except Exception as e:
                print(f"Polling Error: {e}")
                break

if __name__ == "__main__":
    asyncio.run(test_higgsfield_generation())
