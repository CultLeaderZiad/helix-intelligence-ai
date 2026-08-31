import os
import httpx
import base64
import logging
from typing import List, Dict, Any, Optional
from app.services.ai.base import AIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        raw_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY", "")
        self.api_key = raw_key.strip().strip('"\'') if raw_key else ""
        self.model = "gemini-flash-latest"
        self.image_model = getattr(settings, "GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Lightweight connection and authentication test for Gemini API.
        Does NOT generate an expensive image.
        Never logs or exposes the API key.
        """
        if not self.is_configured:
            raise ValueError("No Gemini API key provided")
            
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(test_url)
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "provider": "google_gemini",
                    "model": self.image_model,
                    "message": "Successfully authenticated with Google Gemini"
                }
            elif resp.status_code in (401, 403):
                raise ValueError("Authentication failed: invalid or unauthorized Gemini API key")
            elif resp.status_code == 429:
                raise ValueError("Gemini API rate limit exceeded or quota exhausted")
            else:
                raise ValueError(f"Gemini API returned error {resp.status_code}")

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

        # Models to try for image generation
        candidate_models = [self.image_model]
        for fallback in ["gemini-2.5-flash-image", "gemini-3.1-flash-lite-image", "gemini-3-pro-image"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None
            for model_name in candidate_models:
                generate_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                generate_payload = {
                    "contents": [{"parts": parts}]
                }

                try:
                    resp = await client.post(
                        generate_url,
                        headers={"Content-Type": "application/json"},
                        json=generate_payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            for part in candidates[0].get("content", {}).get("parts", []):
                                inline = part.get("inlineData") or part.get("inline_data")
                                if inline and inline.get("data"):
                                    mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                                    image_bytes = base64.b64decode(inline["data"])
                                    return {
                                        "provider": "gemini",
                                        "model": model_name,
                                        "media_type": "image",
                                        "mime_type": mime_type,
                                        "data": image_bytes,
                                        "metadata": {
                                            "prompt": prompt,
                                            "aspect_ratio": target_ratio,
                                            "model": model_name
                                        }
                                    }
                    elif resp.status_code == 429:
                        last_error = "Gemini API quota exceeded or rate limit reached. Please check your Google AI Studio quota."
                        continue
                    elif resp.status_code == 400:
                        err_msg = resp.json().get("error", {}).get("message", resp.text[:120])
                        last_error = f"Gemini API 400 Bad Request: {err_msg}"
                        continue
                    elif resp.status_code in (401, 403):
                        raise ValueError("Gemini API key is invalid or unauthorized")
                    else:
                        last_error = f"Gemini API returned HTTP {resp.status_code}"
                except Exception as e:
                    if "unauthorized" in str(e).lower() or "invalid" in str(e).lower():
                        raise
                    last_error = str(e)
                    logger.warning("Error with model %s: %s", model_name, e)

            if last_error:
                raise ValueError(last_error)

        raise ValueError("Gemini image generation did not return image data")
