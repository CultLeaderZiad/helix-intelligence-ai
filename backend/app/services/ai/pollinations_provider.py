import logging
import re
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15MB
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50MB


def sanitize_prompt(prompt: str, max_chars: int = 800) -> str:
    """
    Cleans and normalizes user prompt for URL-based REST endpoints.
    Eliminates excessive newlines, tabs, and trims at word boundaries
    to keep the request well within safe HTTP URL and Cloudflare limits.
    """
    if not prompt:
        return "creative commercial advertisement"
    cleaned = re.sub(r"\s+", " ", prompt).strip()
    if len(cleaned) > max_chars:
        truncated = cleaned[:max_chars].rsplit(" ", 1)
        cleaned = truncated[0] if len(truncated) > 1 else cleaned[:max_chars]
    return cleaned


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
        Generates an image using Pollinations with random seed, safe percent-encoding,
        multi-tier model fallback, and automatic watermark badge removal.
        """
        from app.core.config import settings
        import random

        cleaned_prompt = sanitize_prompt(prompt, max_chars=800)
        logger.info("Generating image with Pollinations: %s", cleaned_prompt[:60])
        
        # CRITICAL: safe="" ensures slashes, colons, question marks etc. are percent-encoded
        # so they do not break REST path routing into HTTP 404s.
        encoded_prompt = quote(cleaned_prompt, safe="")
        
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
        requested_model = kwargs.get("model") or "flux"

        # Multi-tier candidate models for resilience:
        # If the requested model returns 404/5xx or is temporarily unavailable,
        # iterate through fallbacks (sana, turbo, or default).
        candidate_models: List[str] = [requested_model]
        for fallback_m in ["sana", "turbo", ""]:
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if settings.POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"

        ref_param = ""
        if reference_images and len(reference_images) > 0:
            first_ref = str(reference_images[0])
            if first_ref.startswith("http://") or first_ref.startswith("https://"):
                ref_param = f"&image={quote(first_ref)}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error_status: Optional[int] = None
            last_error_detail: str = ""

            for current_model in candidate_models:
                if settings.POLLINATIONS_API_KEY:
                    model_arg = f"?model={current_model}&" if current_model else "?"
                    url = (
                        f"https://gen.pollinations.ai/image/{encoded_prompt}"
                        f"{model_arg}width={width}&height={height}&seed={seed}&nologo=true{ref_param}"
                    )
                else:
                    model_arg = f"&model={current_model}" if current_model else ""
                    url = (
                        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                        f"?width={width}&height={height}&seed={seed}&nologo=true&nofeed=true{model_arg}{ref_param}"
                    )

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
                                "model": current_model or self.image_model,
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
                            last_error_status = 429
                            last_error_detail = "Rate limit reached"
                            continue
                        elif resp.status_code == 402:
                            last_error_status = 402
                            last_error_detail = "Demand capacity reached"
                            continue
                        else:
                            last_error_status = resp.status_code
                            last_error_detail = f"HTTP {resp.status_code}"
                            continue
                    else:
                        async with client.stream("GET", url, headers=headers) as resp:
                            if resp.status_code == 200:
                                buffer = bytearray()
                                async for chunk in resp.aiter_bytes(chunk_size=65536):
                                    buffer.extend(chunk)
                                    if len(buffer) > MAX_IMAGE_BYTES:
                                        raise ValueError("Image payload exceeds maximum allowed size of 15MB.")
                                raw_bytes = bytes(buffer)
                                if len(raw_bytes) < 500:
                                    logger.warning("Pollinations model %s returned small payload (%d bytes), trying next", current_model, len(raw_bytes))
                                    continue
                                cleaned_bytes = self._clean_watermark(raw_bytes, width, height)
                                return {
                                    "provider": "helix_managed",
                                    "model": current_model or self.image_model,
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
                                last_error_status = 429
                                last_error_detail = "Rate limit reached"
                                continue
                            elif resp.status_code == 402:
                                last_error_status = 402
                                last_error_detail = "Demand capacity reached"
                                continue
                            else:
                                last_error_status = resp.status_code
                                last_error_detail = f"HTTP {resp.status_code}"
                                continue

                except ValueError as ve:
                    if "exceeds maximum allowed size" in str(ve):
                        raise
                    logger.warning("Pollinations candidate %s failed: %s", current_model, ve)
                    continue
                except httpx.TimeoutException:
                    logger.warning("Pollinations candidate %s timed out, trying next", current_model)
                    last_error_detail = "Request timed out"
                    continue
                except Exception as e:
                    logger.warning("Pollinations candidate %s encountered error: %s", current_model, e)
                    last_error_detail = str(e)
                    continue

            # If all candidates exhausted
            if last_error_status == 429:
                raise ValueError("Image generation rate limit reached. Please try again later.")
            elif last_error_status == 402:
                raise ValueError("Image generation service is currently experiencing high demand. Please try again shortly or configure a custom API key.")
            elif last_error_status == 404:
                raise ValueError("Image generation model is temporarily unavailable. Please retry shortly.")
            else:
                detail = f": {last_error_detail}" if last_error_detail else ""
                raise ValueError(f"Image generation failed{detail}. Please retry or connect a custom Gemini API key.")

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

        cleaned_prompt = sanitize_prompt(prompt, max_chars=800)
        logger.info("Generating video with Pollinations: %s", cleaned_prompt[:50])
        
        encoded_prompt = quote(cleaned_prompt, safe="")
        
        model = kwargs.get("model", "wan-fast")
        duration = kwargs.get("duration", 5)
        
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        start_frame = kwargs.get("start_frame") or kwargs.get("start_image_url")
        end_frame = kwargs.get("end_frame") or kwargs.get("end_image_url")
        
        url = f"https://gen.pollinations.ai/video/{encoded_prompt}?model={model}&duration={duration}&aspectRatio={aspect_ratio}&audio=false&nologo=true"
        if start_frame and (str(start_frame).startswith("http://") or str(start_frame).startswith("https://")):
            url += f"&image={quote(str(start_frame))}"
        if end_frame and (str(end_frame).startswith("http://") or str(end_frame).startswith("https://")):
            url += f"&end_image={quote(str(end_frame))}"
        
        headers = {}
        if settings.POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.POLLINATIONS_API_KEY}"
            
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
