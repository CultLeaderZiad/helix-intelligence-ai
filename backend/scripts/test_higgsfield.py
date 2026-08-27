import asyncio
import httpx
import time
from app.core.config import settings

async def test_higgsfield_generation():
    key_id = settings.HF_API_KEY_ID
    key_secret = settings.HF_API_KEY_SECRET

    if not key_id or not key_secret:
        print("ERROR: HF_API_KEY_ID or HF_API_KEY_SECRET not set in .env.local")
        return

    print(f"Using HF_API_KEY_ID: {key_id}")
    
    headers = {
        "Authorization": f"Key {key_id}:{key_secret}",
        "Content-Type": "application/json",
        "User-Agent": "higgsfield-server-js/2.0"
    }
    
    url = "https://platform.higgsfield.ai/v1/text2image/soul"
    
    # IMAGE_FAST parameters mapped to Higgsfield
    payload = {
        "prompt": "A futuristic city with flying cars at sunset, highly detailed",
        "width_and_height": "1024x1024",
        "quality": "720p",
        "batch_size": 1
    }
    
    start_time = time.time()
    print("Starting generation request to Higgsfield...")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code} - {e.response.text}")
            return
        except Exception as e:
            print(f"Request Error: {e}")
            return
            
        print("Generation job queued:", data)
        request_id = data.get("request_id")
        
        if not request_id:
            print("No request_id returned in response")
            return
            
        # Polling
        polling_url = f"https://platform.higgsfield.ai/requests/{request_id}/status"
        
        while True:
            await asyncio.sleep(2.0)
            print(f"Polling {polling_url}...")
            
            try:
                poll_resp = await client.get(polling_url, headers=headers, timeout=10.0)
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                
                status = poll_data.get("status")
                print(f"Status: {status}")
                
                if status in ["completed", "failed", "nsfw"]:
                    latency = time.time() - start_time
                    print(f"\nFinished with status: {status}")
                    print(f"Latency: {latency:.2f} seconds")
                    
                    if status == "completed":
                        images = poll_data.get("images", [])
                        if images:
                            print(f"Media URL: {images[0].get('url')}")
                        else:
                            print("No images found in response")
                            
                    print(f"Full response: {poll_data}")
                    break
                    
            except httpx.HTTPStatusError as e:
                print(f"Polling HTTP Error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"Polling Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_higgsfield_generation())
