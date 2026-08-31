import logging
import httpx
from typing import Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class PollinationsProvider:
    """
    Completely free image & video generation provider using Pollinations.ai.
    Uses the authenticated gen.pollinations.ai API if a key is provided,
    otherwise falls back to the anonymous image.pollinations.ai endpoint.
    """
    
    def __init__(self):
        self.image_model = "pollinations-free-image"
        
    @property
    def is_configured(self) -> bool:
        return True  # Always configured since it requires no keys (acts as free tier)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Lightweight connection test for Pollinations.
        """
        from app.core.config import settings
        headers = {}
        if settings.POLLINATIONS_API_KEY:
            url = "https://gen.pollinations.ai/image/test"
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"
        else:
            url = "https://image.pollinations.ai/prompt/test"
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "provider": "pollinations",
                    "model": self.image_model,
                    "message": "Successfully connected to Pollinations.ai"
                }
            raise ValueError(f"Failed to connect to Pollinations API: HTTP {resp.status_code}")

    async def generate_image(self, prompt: str, reference_images: list = None, **kwargs) -> Dict[str, Any]:
        """
        Generates an image using Pollinations.
        """
        from app.core.config import settings
        logger.info("Generating image with Pollinations: %s", prompt[:50])
        
        encoded_prompt = quote(prompt)
        
        # Default dimensions for 1:1
        width = 1024
        height = 1024
        
        aspect_ratio = kwargs.get("aspect_ratio", "1:1")
        if aspect_ratio == "16:9":
            width, height = 1280, 720
        elif aspect_ratio == "9:16":
            width, height = 720, 1280
        elif aspect_ratio == "3:4":
            width, height = 768, 1024
        elif aspect_ratio == "4:3":
            width, height = 1024, 768
            
        headers = {}
        if settings.POLLINATIONS_API_KEY:
            url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width={width}&height={height}&nologo=true"
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"
        else:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    image_bytes = resp.content
                    return {
                        "provider": "pollinations",
                        "model": self.image_model,
                        "media_type": "image",
                        "mime_type": "image/jpeg",
                        "data": image_bytes,
                        "metadata": {
                            "prompt": prompt,
                            "aspect_ratio": aspect_ratio,
                            "model": self.image_model
                        }
                    }
                elif resp.status_code == 429:
                    raise ValueError("Pollinations API rate limit reached. Please try again later.")
                else:
                    raise ValueError(f"Pollinations API error: HTTP {resp.status_code}")
                    
            except httpx.TimeoutException:
                raise ValueError("Pollinations API request timed out after 60 seconds.")
            except Exception as e:
                logger.error("Pollinations generation error: %s", e)
                raise ValueError(f"Image generation failed: {str(e)}")

    async def generate_video(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generates a video using Pollinations /video/{prompt} endpoint.
        """
        from app.core.config import settings
        logger.info("Generating video with Pollinations: %s", prompt[:50])
        
        encoded_prompt = quote(prompt)
        
        model = kwargs.get("model", "wan-fast")
        duration = kwargs.get("duration", 5)
        
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        
        url = f"https://gen.pollinations.ai/video/{encoded_prompt}?model={model}&duration={duration}&aspectRatio={aspect_ratio}&audio=false&nologo=true"
        
        headers = {}
        if settings.POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    video_bytes = resp.content
                    return {
                        "provider": "pollinations",
                        "model": model,
                        "media_type": "video",
                        "mime_type": "video/mp4",
                        "data": video_bytes,
                        "metadata": {
                            "prompt": prompt,
                            "aspect_ratio": aspect_ratio,
                            "model": model,
                            "duration": duration
                        }
                    }
                elif resp.status_code == 402:
                    raise ValueError("Insufficient Pollen balance on the Pollinations API key to run this model.")
                elif resp.status_code == 429:
                    raise ValueError("Pollinations API rate limit reached. Please try again later.")
                else:
                    raise ValueError(f"Pollinations API error: HTTP {resp.status_code}")
            except httpx.TimeoutException:
                raise ValueError("Pollinations API request timed out after 120 seconds.")
            except Exception as e:
                logger.error("Pollinations video generation error: %s", e)
                raise ValueError(f"Video generation failed: {str(e)}")
