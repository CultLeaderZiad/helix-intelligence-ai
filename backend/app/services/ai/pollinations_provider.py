import logging
import httpx
from typing import Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class PollinationsProvider:
    """
    Completely free image generation provider using Pollinations.ai.
    Requires no API keys and has no hard rate limits.
    """
    
    def __init__(self):
        self.image_model = "pollinations-free-image"
        
    @property
    def is_configured(self) -> bool:
        return True  # Always configured since it requires no keys

    async def test_connection(self) -> Dict[str, Any]:
        """
        Lightweight connection test for Pollinations.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://image.pollinations.ai/prompt/test")
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
        logger.info("Generating image with Pollinations: %s", prompt[:50])
        
        # Pollinations supports direct URL encoding of the prompt
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
            
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(url)
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
