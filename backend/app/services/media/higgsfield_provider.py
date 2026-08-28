import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class HiggsfieldProvider:
    def __init__(self):
        self.key_id = settings.HF_API_KEY_ID
        self.key_secret = settings.HF_API_KEY_SECRET
        self.base_url = "https://platform.higgsfield.ai"
        
    @property
    def headers(self):
        if not self.key_id or not self.key_secret:
            raise ValueError("Higgsfield API credentials not configured (HF_API_KEY_ID / HF_API_KEY_SECRET)")
            
        return {
            "Authorization": f"Key {self.key_id}:{self.key_secret}",
            "Content-Type": "application/json",
            "User-Agent": "higgsfield-server-js/2.0"
        }
        
    async def generate_media(self, prompt: str, parameters: dict) -> str:
        """
        Submits a generation request to Higgsfield and returns the request_id.
        Raises an exception if the request fails.
        """
        # Map parameters for Higgsfield
        payload = {
            "params": {
                "prompt": prompt,
                "width_and_height": parameters.get("resolution", "1024x1024"),
                "quality": parameters.get("quality", "720p"),
                "batch_size": 1
            }
        }
        
        if "webhook" in parameters:
            payload["webhook"] = {
                "url": parameters["webhook"],
                "secret": parameters.get("webhook_secret", "helix_webhook_secret")
            }
        
        endpoint = f"{self.base_url}/v1/text2image/soul"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(endpoint, json=payload, headers=self.headers, timeout=30.0)
            
            if resp.status_code != 200:
                logger.error(f"Higgsfield generation failed: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
                
            data = resp.json()
            request_id = data.get("request_id")
            
            if not request_id:
                raise ValueError(f"No request_id returned from Higgsfield. Response: {data}")
                
            return request_id

    async def check_status(self, request_id: str) -> dict:
        """
        Checks the status of a generation request.
        Returns a dict with 'status' (completed, failed, in_progress, etc.) and 'url' if completed.
        """
        endpoint = f"{self.base_url}/requests/{request_id}/status"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(endpoint, headers=self.headers, timeout=10.0)
            
            if resp.status_code != 200:
                logger.error(f"Higgsfield status check failed: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
                
            data = resp.json()
            status = data.get("status")
            
            result = {"status": status, "raw": data}
            
            if status == "completed":
                images = data.get("images", [])
                if images and len(images) > 0:
                    result["url"] = images[0].get("url")
            
            return result
