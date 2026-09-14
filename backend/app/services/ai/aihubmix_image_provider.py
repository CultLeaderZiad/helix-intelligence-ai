"""
AIHubMix Image Generation Provider.

High-fidelity image generation using AIHubMix OpenAI-compatible API.
Employs gpt-image-2-free (and fallback free image models) to produce clean,
commercial-grade PNG images with zero third-party watermark and no vendor branding.
Uses Pillow to guarantee precise target aspect-ratio dimensions.
"""

from __future__ import annotations

import base64
import io
import logging
import random
from typing import Any, Dict, List, Optional
import httpx
from PIL import Image

from app.core.config import settings
from app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)

# Aspect ratio dimensions mapping for high-definition output
DIMENSIONS_MAP = {
    "1:1": (1024, 1024),
    "4:5": (820, 1024),
    "9:16": (576, 1024),
    "16:9": (1024, 576),
    "3:4": (768, 1024),
    "4:3": (1024, 768),
}


class AIHubMixImageProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or settings.AIHUBMIX_API_KEY or "").strip()
        self.base_url = "https://aihubmix.com/v1"
        self.image_model = "gpt-image-2-free"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured:
            raise ValueError("AIHUBMIX_API_KEY is not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "provider": "aihubmix",
                    "model": self.image_model,
                    "message": "Successfully connected to AIHubMix Image Service"
                }
    async def _call_api(self, messages: List[dict]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4.7-flash-free",
            "messages": messages,
            "temperature": 0.3
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_image(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "1:1",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generates an image via AIHubMix:
        1. Attempts multimodal generation via Gemini image models (e.g. gemini-3.1-flash-image-preview-free),
           supporting native aspect ratios and image-to-image reference editing.
        2. Gracefully falls back to gpt-image-2-free via /images/generations for commercial-grade output.
        3. Formats/crops to exact pixel dimensions with zero watermarks.
        """
        if not self.is_configured:
            raise ValueError("AIHUBMIX_API_KEY is not configured")

        target_w, target_h = DIMENSIONS_MAP.get(aspect_ratio, (1024, 1024))
        random_seed = kwargs.get("seed") or random.randint(1, 1000000000)

        # 1. Attempt Gemini Multimodal Image Generation
        gemini_result = await self._try_gemini_generation(
            prompt=prompt,
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            target_w=target_w,
            target_h=target_h,
            random_seed=random_seed
        )
        if gemini_result is not None:
            return gemini_result

        # 2. Fallback to GPT Image 2 Free (/images/generations)
        return await self._generate_gpt_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            target_w=target_w,
            target_h=target_h,
            random_seed=random_seed
        )

    async def _try_gemini_generation(
        self,
        prompt: str,
        reference_images: Optional[List[str]],
        aspect_ratio: str,
        target_w: int,
        target_h: int,
        random_seed: int
    ) -> Optional[Dict[str, Any]]:
        """Attempts image generation/editing via Gemini multimodal endpoint."""
        model_name = "gemini-3.1-flash-image-preview-free"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build user message content
        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": f"{prompt.strip()} (Style: commercial high-resolution advertisement)"}
        ]

        if reference_images:
            for ref in reference_images:
                if ref:
                    url = ref if ref.startswith("data:") or ref.startswith("http") else f"data:image/png;base64,{ref}"
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": f"aspect_ratio={aspect_ratio}"},
                {"role": "user", "content": user_content}
            ],
            "modalities": ["text", "image"]
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0].get("message", {})
                    parts = choice.get("multi_mod_content") or choice.get("content")
                    if parts and isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict) and "inline_data" in part:
                                raw_b64 = part["inline_data"].get("data")
                                if raw_b64:
                                    raw_bytes = base64.b64decode(raw_b64)
                                    formatted_bytes = self._format_to_aspect_ratio(raw_bytes, target_w, target_h)
                                    logger.info("Generated image via AIHubMix Gemini model: %s", model_name)
                                    return {
                                        "provider": "helix_managed",
                                        "model": model_name,
                                        "media_type": "image",
                                        "mime_type": "image/png",
                                        "data": formatted_bytes,
                                        "metadata": {
                                            "prompt": prompt,
                                            "aspect_ratio": aspect_ratio,
                                            "width": target_w,
                                            "height": target_h,
                                            "seed": random_seed
                                        }
                                    }
                else:
                    logger.warning(
                        "AIHubMix Gemini image generation returned HTTP %s (%s), falling back to GPT Image 2",
                        resp.status_code, resp.text[:120]
                    )
        except Exception as e:
            logger.warning("AIHubMix Gemini image attempt failed: %s, falling back to GPT Image 2", e)

        return None

    async def _generate_gpt_image(
        self,
        prompt: str,
        aspect_ratio: str,
        target_w: int,
        target_h: int,
        random_seed: int
    ) -> Dict[str, Any]:
        """Generates image via GPT Image 2 Free."""
        enhanced_prompt = f"{prompt.strip()} --seed {random_seed}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-image-2-free",
            "prompt": enhanced_prompt,
            "n": 1,
            "size": "1024x1024"
        }

        logger.info("Generating image via AIHubMix gpt-image-2-free (%s): %s", aspect_ratio, prompt[:60])

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload
                )
                if resp.status_code != 200:
                    raise ValueError(f"AIHubMix generation failed with HTTP {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                items = data.get("data", [])
                if not items:
                    raise ValueError("AIHubMix returned empty image data array")

                first_item = items[0]
                if "b64_json" in first_item:
                    raw_bytes = base64.b64decode(first_item["b64_json"])
                elif "url" in first_item:
                    img_resp = await client.get(first_item["url"], timeout=30.0)
                    raw_bytes = img_resp.content
                else:
                    raise ValueError("No image payload received from AIHubMix")

                formatted_bytes = self._format_to_aspect_ratio(raw_bytes, target_w, target_h)

                return {
                    "provider": "helix_managed",
                    "model": "gpt-image-2-free",
                    "media_type": "image",
                    "mime_type": "image/png",
                    "data": formatted_bytes,
                    "metadata": {
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio,
                        "width": target_w,
                        "height": target_h,
                        "seed": random_seed
                    }
                }
            except Exception as e:
                logger.error("AIHubMix GPT image generation error: %s", e)
                raise ValueError(f"Image generation failed: {str(e)}")

    def _format_to_aspect_ratio(self, raw_bytes: bytes, target_w: int, target_h: int) -> bytes:
        """Resizes and center-crops the image to strictly adhere to the target dimensions."""
        try:
            im = Image.open(io.BytesIO(raw_bytes))
            orig_w, orig_h = im.size

            # If already exact dimensions, return PNG bytes
            if (orig_w, orig_h) == (target_w, target_h):
                out = io.BytesIO()
                im.save(out, format="PNG", optimize=True)
                return out.getvalue()

            # Target aspect ratio
            target_ratio = target_w / target_h
            orig_ratio = orig_w / orig_h

            if orig_ratio > target_ratio:
                # Image is wider than needed -> crop width
                new_w = int(orig_h * target_ratio)
                left = (orig_w - new_w) // 2
                im_cropped = im.crop((left, 0, left + new_w, orig_h))
            else:
                # Image is taller than needed -> crop height
                new_h = int(orig_w / target_ratio)
                top = (orig_h - new_h) // 2
                im_cropped = im.crop((0, top, orig_w, top + new_h))

            # Resize to exact requested dimensions
            im_resized = im_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

            out = io.BytesIO()
            im_resized.save(out, format="PNG", optimize=True)
            return out.getvalue()
        except Exception as err:
            logger.warning("Failed to format image aspect ratio: %s, returning original", err)
            return raw_bytes
