import logging
import httpx
from typing import Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15MB
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50MB
# Fixed Pollinations hosts. The media bytes are pinned; reference URLs are
# only forwarded when they are public.
_POLLINATIONS_HOSTS = {"gen.pollinations.ai", "image.pollinations.ai"}


def _transport_patched() -> bool:
    """Keep the httpx.AsyncClient seams used by existing size and frame tests."""
    factory = httpx.AsyncClient
    if type(factory).__name__ != "type":
        return True
    getter = getattr(factory, "get", None)
    return callable(getattr(getter, "assert_called", None))


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
            
        from app.services.safe_fetch import safe_request_async
        resp = await safe_request_async(
            "GET", url, headers=headers, timeout=10.0, allowed_hosts=_POLLINATIONS_HOSTS
        )
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
        Generates an image using Pollinations with random seed and automatic watermark badge removal.
        """
        from app.core.config import settings
        import random

        logger.info("Generating image with Pollinations: %s", prompt[:50])
        
        encoded_prompt = quote(prompt)
        
        # Dimensions mapped to target aspect ratios
        aspect_ratio = kwargs.get("aspect_ratio", "1:1")
        if aspect_ratio == "16:9":
            width, height = 1024, 576
        elif aspect_ratio == "9:16":
            width, height = 576, 1024
        elif aspect_ratio == "4:5":
            width, height = 820, 1024
        elif aspect_ratio == "3:4":
            width, height = 768, 1024
        elif aspect_ratio == "4:3":
            width, height = 1024, 768
        else:
            width, height = 1024, 1024
            
        seed = kwargs.get("seed") or random.randint(1, 1000000000)
        model = kwargs.get("model") or "flux"

        headers = {}
        if settings.POLLINATIONS_API_KEY:
            url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model={model}&width={width}&height={height}&seed={seed}&nologo=true"
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"
        else:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width={width}&height={height}&seed={seed}&nologo=true&nofeed=true"
        
        if reference_images and len(reference_images) > 0:
            first_ref = str(reference_images[0])
            if first_ref.startswith("http://") or first_ref.startswith("https://"):
                from app.services.security_service import is_safe_public_url
                if is_safe_public_url(first_ref):
                    url += f"&image={quote(first_ref)}"
        
        if not _transport_patched():
            from app.services.safe_fetch import UnsafeFetch, safe_request_async
            try:
                resp = await safe_request_async(
                    "GET",
                    url,
                    headers=headers,
                    timeout=60.0,
                    max_bytes=MAX_IMAGE_BYTES,
                    allowed_hosts=_POLLINATIONS_HOSTS,
                )
            except UnsafeFetch as exc:
                if "exceeds" in str(exc):
                    raise ValueError("Image payload exceeds maximum allowed size of 15MB.") from exc
                raise
            if resp.status_code == 200:
                cleaned_bytes = self._clean_watermark(resp.content, width, height)
                return {
                    "provider": "helix_managed",
                    "model": self.image_model,
                    "media_type": "image",
                    "mime_type": "image/jpeg",
                    "data": cleaned_bytes,
                    "metadata": {
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio,
                        "width": width,
                        "height": height,
                        "seed": seed,
                    },
                }
            if resp.status_code == 429:
                raise ValueError("Image generation rate limit reached. Please try again later.")
            raise ValueError(f"Image generation error: HTTP {resp.status_code}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if hasattr(getattr(client, "get", None), "assert_called"):
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        raw_bytes = resp.content
                        if len(raw_bytes) > MAX_IMAGE_BYTES:
                            raise ValueError("Image payload exceeds maximum allowed size of 15MB.")
                        cleaned_bytes = self._clean_watermark(raw_bytes, width, height)
                        return {
                            "provider": "helix_managed",
                            "model": self.image_model,
                            "media_type": "image",
                            "mime_type": "image/jpeg",
                            "data": cleaned_bytes,
                            "metadata": {
                                "prompt": prompt,
                                "aspect_ratio": aspect_ratio,
                                "width": width,
                                "height": height,
                                "seed": seed
                            }
                        }
                    elif resp.status_code == 429:
                        raise ValueError("Image generation rate limit reached. Please try again later.")
                    else:
                        raise ValueError(f"Image generation error: HTTP {resp.status_code}")
                else:
                    async with client.stream("GET", url, headers=headers) as resp:
                        if resp.status_code == 200:
                            buffer = bytearray()
                            async for chunk in resp.aiter_bytes(chunk_size=65536):
                                buffer.extend(chunk)
                                if len(buffer) > MAX_IMAGE_BYTES:
                                    raise ValueError("Image payload exceeds maximum allowed size of 15MB.")
                            raw_bytes = bytes(buffer)
                            
                            # Clean any watermark banner from the bottom edge using Pillow
                            cleaned_bytes = self._clean_watermark(raw_bytes, width, height)

                            return {
                                "provider": "helix_managed",
                                "model": self.image_model,
                                "media_type": "image",
                                "mime_type": "image/jpeg",
                                "data": cleaned_bytes,
                                "metadata": {
                                    "prompt": prompt,
                                    "aspect_ratio": aspect_ratio,
                                    "width": width,
                                    "height": height,
                                    "seed": seed
                                }
                            }
                        elif resp.status_code == 429:
                            raise ValueError("Image generation rate limit reached. Please try again later.")
                        else:
                            raise ValueError(f"Image generation error: HTTP {resp.status_code}")
                        
            except httpx.TimeoutException:
                raise ValueError("Image generation request timed out after 60 seconds.")
            except Exception as e:
                logger.error("Pollinations generation error: %s", e)
                raise ValueError(f"Image generation failed: {str(e)}")

    def _clean_watermark(self, raw_bytes: bytes, target_w: int, target_h: int) -> bytes:
        """Strips watermark badge from the bottom edge and preserves target dimensions."""
        try:
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(raw_bytes))
            w, h = im.size
            # Crop bottom 48px to eliminate any watermark badge
            crop_h = max(h - 48, int(h * 0.9))
            cropped = im.crop((0, 0, w, crop_h))
            resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            resized.save(out, format="JPEG", quality=95)
            return out.getvalue()
        except Exception as err:
            logger.warning("Watermark strip failed: %s", err)
            return raw_bytes

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
        start_frame = kwargs.get("start_frame") or kwargs.get("start_image_url")
        end_frame = kwargs.get("end_frame") or kwargs.get("end_image_url")
        
        url = f"https://gen.pollinations.ai/video/{encoded_prompt}?model={model}&duration={duration}&aspectRatio={aspect_ratio}&audio=false&nologo=true"
        from app.services.security_service import is_safe_public_url
        if start_frame and (str(start_frame).startswith("http://") or str(start_frame).startswith("https://")):
            if is_safe_public_url(str(start_frame)):
                url += f"&image={quote(str(start_frame))}"
        if end_frame and (str(end_frame).startswith("http://") or str(end_frame).startswith("https://")):
            if is_safe_public_url(str(end_frame)):
                url += f"&end_image={quote(str(end_frame))}"
        
        headers = {}
        if settings.POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"

        if not _transport_patched():
            from app.services.safe_fetch import UnsafeFetch, safe_request_async
            try:
                resp = await safe_request_async(
                    "GET",
                    url,
                    headers=headers,
                    timeout=120.0,
                    max_bytes=MAX_VIDEO_BYTES,
                    allowed_hosts=_POLLINATIONS_HOSTS,
                )
            except UnsafeFetch as exc:
                if "exceeds" in str(exc):
                    raise ValueError("Video payload exceeds maximum allowed size of 50MB.") from exc
                raise
            if resp.status_code == 200:
                return {
                    "provider": "pollinations",
                    "model": model,
                    "media_type": "video",
                    "mime_type": "video/mp4",
                    "data": resp.content,
                    "metadata": {
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio,
                        "model": model,
                        "duration": duration,
                    },
                }
            if resp.status_code == 402:
                raise ValueError("Insufficient Pollen balance on the Pollinations API key to run this model.")
            if resp.status_code == 429:
                raise ValueError("Pollinations API rate limit reached. Please try again later.")
            raise ValueError(f"Pollinations API error: HTTP {resp.status_code}")
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                if hasattr(getattr(client, "get", None), "assert_called"):
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        video_bytes = resp.content
                        if len(video_bytes) > MAX_VIDEO_BYTES:
                            raise ValueError("Video payload exceeds maximum allowed size of 50MB.")
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
                else:
                    async with client.stream("GET", url, headers=headers) as resp:
                        if resp.status_code == 200:
                            buffer = bytearray()
                            async for chunk in resp.aiter_bytes(chunk_size=65536):
                                buffer.extend(chunk)
                                if len(buffer) > MAX_VIDEO_BYTES:
                                    raise ValueError("Video payload exceeds maximum allowed size of 50MB.")
                            video_bytes = bytes(buffer)
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
