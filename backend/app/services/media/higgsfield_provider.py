import httpx
import logging
from urllib.parse import quote
from typing import Any, Optional, Dict, List
from app.core.config import settings
from app.services.media.higgsfield_registry import (
    get_base_url,
    resolve_capability,
    resolve_endpoint_url,
    list_available_capabilities,
    SEMANTIC_CAPABILITIES,
)

logger = logging.getLogger(__name__)

class HiggsfieldProvider:
    def __init__(self):
        raw_key_id = (getattr(settings, "HF_API_KEY_ID", "") or "").strip().strip('"\'')
        raw_key_secret = (getattr(settings, "HF_API_KEY_SECRET", "") or "").strip().strip('"\'')
        
        # Handle case where key_id:key_secret was passed in a single variable
        if ":" in raw_key_id and not raw_key_secret:
            parts = raw_key_id.split(":", 1)
            raw_key_id = parts[0].strip()
            raw_key_secret = parts[1].strip()

        self.key_id = raw_key_id
        self.key_secret = raw_key_secret
        self.base_url = get_base_url()

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    @property
    def headers(self) -> dict:
        if not self.is_configured:
            raise ValueError(
                "Higgsfield API credentials not configured. Please verify HF_API_KEY_ID and HF_API_KEY_SECRET on Render."
            )
        # Official Auth format: Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET} (NOT Bearer)
        return {
            "Authorization": f"Key {self.key_id}:{self.key_secret}",
            "hf-api-key": self.key_id,
            "hf-secret": self.key_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_health(self) -> Dict[str, Any]:
        """
        Diagnostic check against {HIGGSFIELD_BASE_URL}/models.
        Never leaks raw keys or headers.
        """
        if not self.is_configured:
            return {
                "provider": "higgsfield",
                "configured": False,
                "authenticated": False,
                "base_url": self.base_url,
                "error": "Missing HF_API_KEY_ID or HF_API_KEY_SECRET"
            }

        endpoint = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(endpoint, headers=self.headers, timeout=12.0)
                if resp.status_code == 200:
                    data = resp.json()
                    models_list = data if isinstance(data, list) else data.get("models", data.get("data", []))
                    
                    sanitized_models = []
                    for m in models_list:
                        if isinstance(m, dict):
                            sanitized_models.append({
                                "slug": m.get("slug") or m.get("id") or m.get("name"),
                                "name": m.get("name") or m.get("title") or m.get("slug"),
                                "type": m.get("type") or m.get("operation_type"),
                            })
                        elif isinstance(m, str):
                            sanitized_models.append({"slug": m, "name": m})

                    return {
                        "provider": "higgsfield",
                        "configured": True,
                        "authenticated": True,
                        "base_url": self.base_url,
                        "model_count": len(models_list),
                        "available_models": sanitized_models or list_available_capabilities()
                    }
                else:
                    return {
                        "provider": "higgsfield",
                        "configured": True,
                        "authenticated": False,
                        "status_code": resp.status_code,
                        "base_url": self.base_url,
                        "error": resp.text[:200]
                    }
        except Exception as e:
            logger.error("Higgsfield health check error: %s", str(e))
            return {
                "provider": "higgsfield",
                "configured": True,
                "authenticated": False,
                "base_url": self.base_url,
                "error": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """Returns catalog of supported semantic capabilities."""
        return list_available_capabilities()

    async def generate_media(
        self,
        prompt: str,
        parameters: Optional[dict] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Submit media generation to Higgsfield. Returns provider request_id.
        """
        parameters = parameters or {}
        mode_or_cap = (
            parameters.get("capability") or 
            parameters.get("mode") or 
            parameters.get("model") or 
            parameters.get("kind")
        )
        cap_spec = resolve_capability(mode_or_cap)
        url = resolve_endpoint_url(cap_spec)

        # Append webhook URL if provided
        if webhook_url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}hf_webhook={quote(webhook_url, safe='')}"

        # Payload construction
        body: Dict[str, Any] = {"prompt": prompt}
        for k, v in cap_spec.get("default_params", {}).items():
            body[k] = v

        for key in (
            "seed",
            "aspect_ratio",
            "duration",
            "image_url",
            "start_image_url",
            "end_image_url",
            "batch_size",
            "quality",
            "negative_prompt"
        ):
            if parameters.get(key) is not None:
                body[key] = parameters[key]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, json=body, headers=self.headers, timeout=60.0
            )
            if resp.status_code >= 400:
                logger.error(
                    "Higgsfield generation failed [%s] on %s: %s",
                    resp.status_code,
                    url,
                    resp.text
                )
                resp.raise_for_status()

            data = resp.json()
            request_id = data.get("request_id")
            if not request_id:
                raise ValueError(f"No request_id returned from Higgsfield: {data}")
            
            logger.info("Higgsfield generation queued successfully with request_id=%s", request_id)
            return request_id

    async def check_status(self, request_id: str) -> dict:
        """
        Poll GET {HIGGSFIELD_BASE_URL}/requests/{request_id}/status
        """
        endpoint = f"{self.base_url}/requests/{request_id}/status"
        async with httpx.AsyncClient() as client:
            resp = await client.get(endpoint, headers=self.headers, timeout=30.0)
            if resp.status_code >= 400:
                logger.error(
                    "Higgsfield status check failed [%s]: %s", resp.status_code, resp.text
                )
                resp.raise_for_status()

            data = resp.json()
            status = data.get("status")
            result: dict[str, Any] = {"status": status, "raw": data}

            images = data.get("images") or []
            video = data.get("video")
            nested = data.get("payload") or {}
            if not images and isinstance(nested, dict):
                images = nested.get("images") or []
                video = video or nested.get("video")

            if status == "completed":
                if images and isinstance(images, list) and isinstance(images[0], dict) and images[0].get("url"):
                    result["url"] = images[0]["url"]
                elif isinstance(video, dict) and video.get("url"):
                    result["url"] = video["url"]
                elif isinstance(data.get("url"), str):
                    result["url"] = data["url"]

            return result
