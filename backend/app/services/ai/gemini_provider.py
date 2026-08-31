import os
import httpx
import base64
import logging
from typing import List, Dict, Any, Optional
from app.services.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    def __init__(self):
        raw_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY", "")
        self.api_key = raw_key.strip().strip('"\'') if raw_key else ""
        self.model = "gemini-flash-latest"
        self.image_model = getattr(settings, "GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _call_api(self, messages: List[dict]) -> str:
        if not self.is_configured:
            raise Exception("GEMINI_API_KEY not configured")
            
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": gemini_messages,
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.2
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_image(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "1:1",
        image_size: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate image using Google's official Gemini/Imagen API.
        Never logs or leaks GEMINI_API_KEY.
        Returns normalized provider dictionary with raw binary bytes in ['data'].
        """
        if not self.is_configured:
            raise ValueError("GEMINI_API_KEY is not configured on this server")

        aspect_ratio_map = {
            "1:1": "1:1",
            "4:5": "4:5",
            "9:16": "9:16",
            "16:9": "16:9",
            "3:4": "3:4",
            "4:3": "4:3",
        }
        target_ratio = aspect_ratio_map.get(aspect_ratio, "1:1")

        # Multimodal request payload construction
        parts: List[Dict[str, Any]] = [{"text": prompt}]

        # Add reference images if provided (URLs or base64)
        if reference_images:
            for ref_url in reference_images[:2]: # Capped to at most 2 references
                if ref_url.startswith("data:image/") and ";base64," in ref_url:
                    header, b64_data = ref_url.split(";base64,", 1)
                    mime = header.replace("data:", "")
                    parts.append({
                        "inline_data": {
                            "mime_type": mime,
                            "data": b64_data
                        }
                    })
                elif ref_url.startswith("http://") or ref_url.startswith("https://"):
                    # Download image bytes safely
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as img_client:
                            img_resp = await img_client.get(ref_url)
                            if img_resp.status_code == 200:
                                mime = img_resp.headers.get("content-type", "image/jpeg").split(";")[0]
                                b64_data = base64.b64encode(img_resp.content).decode("utf-8")
                                parts.append({
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": b64_data
                                    }
                                })
                    except Exception as err:
                        logger.warning("Failed to fetch reference image %s: %s", ref_url, err)

        # Primary attempt using Imagen / Gemini Flash Image endpoint (:predict)
        predict_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:predict?key={self.api_key}"
        predict_payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "aspectRatio": target_ratio,
                "sampleCount": 1,
                "outputMimeType": "image/png"
            }
        }

        # Secondary fallback attempt using generateContent
        generate_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:generateContent?key={self.api_key}"
        generate_payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseMimeType": "image/png"
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            # 1. Try predict format
            try:
                resp = await client.post(
                    predict_url,
                    headers={"Content-Type": "application/json"},
                    json=predict_payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    predictions = data.get("predictions", [])
                    if predictions and isinstance(predictions, list):
                        img_dict = predictions[0]
                        b64_str = img_dict.get("bytesBase64Encoded") or img_dict.get("image", {}).get("imageBytes")
                        if b64_str:
                            image_bytes = base64.b64decode(b64_str)
                            return {
                                "provider": "gemini",
                                "model": self.image_model,
                                "media_type": "image",
                                "mime_type": "image/png",
                                "data": image_bytes,
                                "metadata": {
                                    "prompt": prompt,
                                    "aspect_ratio": target_ratio,
                                    "model": self.image_model
                                }
                            }
            except Exception as e:
                logger.warning("Gemini predict endpoint error: %s. Trying generateContent fallback...", e)

            # 2. Try generateContent format
            try:
                resp2 = await client.post(
                    generate_url,
                    headers={"Content-Type": "application/json"},
                    json=generate_payload
                )
                if resp2.status_code == 429:
                    raise Exception("provider_rate_limited")
                if resp2.status_code == 200:
                    data = resp2.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        for part in candidates[0].get("content", {}).get("parts", []):
                            inline = part.get("inlineData") or part.get("inline_data")
                            if inline and inline.get("data"):
                                mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                                image_bytes = base64.b64decode(inline["data"])
                                return {
                                    "provider": "gemini",
                                    "model": self.image_model,
                                    "media_type": "image",
                                    "mime_type": mime_type,
                                    "data": image_bytes,
                                    "metadata": {
                                        "prompt": prompt,
                                        "aspect_ratio": target_ratio,
                                        "model": self.image_model
                                    }
                                }
                elif resp2.status_code == 429:
                    raise Exception("provider_rate_limited")
                elif resp2.status_code == 400:
                    err_msg = resp2.json().get("error", {}).get("message", resp2.text[:100])
                    raise ValueError(f"Gemini API 400 Bad Request: {err_msg}")
                elif resp2.status_code == 403 or resp2.status_code == 401:
                    raise ValueError("Gemini API key is invalid or unauthorized")
            except Exception as e:
                if "provider_rate_limited" in str(e):
                    raise
                logger.error("Gemini generateContent error: %s", e)
                raise

        raise ValueError("Gemini image generation did not return image data")
