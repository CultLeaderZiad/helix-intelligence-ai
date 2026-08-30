import httpx
import logging
from urllib.parse import quote
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Official base URL (docs quickstart: https://docs.higgsfield.ai/docs/quickstart)
from app.services.media.higgsfield_registry import (
    HF_API_BASE,
    resolve_mode_spec,
    resolve_endpoint_url,
    MODEL_REGISTRY,
)

class HiggsfieldProvider:
    def __init__(self):
        raw_key_id = getattr(settings, "HF_API_KEY_ID", "") or ""
        raw_key_secret = getattr(settings, "HF_API_KEY_SECRET", "") or ""
        self.key_id = raw_key_id.strip().strip('"\'')
        self.key_secret = raw_key_secret.strip().strip('"\'')

    @property
    def headers(self) -> dict:
        if not self.key_id or not self.key_secret:
            raise ValueError(
                "Higgsfield API credentials not configured "
                "(HF_API_KEY_ID / HF_API_KEY_SECRET)"
            )
        # Official Auth format: Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET} (NOT Bearer)
        return {
            "Authorization": f"Key {self.key_id}:{self.key_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _resolve_endpoint(self, parameters: dict) -> str:
        mode = (parameters or {}).get("mode") or (parameters or {}).get("model") or (parameters or {}).get("kind")
        mode_spec = resolve_mode_spec(mode)
        return resolve_endpoint_url(mode_spec)

    async def generate_media(
        self,
        prompt: str,
        parameters: Optional[dict] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Submit generation. Returns request_id.
        Webhook is passed as ?hf_webhook= per official docs.
        """
        parameters = parameters or {}
        mode = parameters.get("mode") or parameters.get("model") or parameters.get("kind")
        mode_spec = resolve_mode_spec(mode)
        url = resolve_endpoint_url(mode_spec)

        if webhook_url:
            url = f"{url}?hf_webhook={quote(webhook_url, safe='')}"

        # Build payload with model defaults and user overrides
        body: dict[str, Any] = {"prompt": prompt}
        
        # Merge default params from mode spec
        for k, v in mode_spec.get("default_params", {}).items():
            body[k] = v

        # User overrides and passthroughs
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
                    "Higgsfield submit failed with HTTP %s: %s", resp.status_code, resp.text
                )
                resp.raise_for_status()

            data = resp.json()
            request_id = data.get("request_id")
            if not request_id:
                raise ValueError(f"No request_id returned from Higgsfield: {data}")
            logger.info("Higgsfield generation successfully queued with request_id=%s", request_id)
            return request_id

    async def check_status(self, request_id: str) -> dict:
        """
        Poll GET /requests/{id}/status.
        Returns { status, url?, raw }.
        Status endpoint may put images at top-level; webhooks nest under payload.
        """
        endpoint = f"{HF_API_BASE}/requests/{request_id}/status"
        async with httpx.AsyncClient() as client:
            resp = await client.get(endpoint, headers=self.headers, timeout=30.0)
            if resp.status_code >= 400:
                logger.error(
                    "Higgsfield status check failed with HTTP %s: %s", resp.status_code, resp.text
                )
                resp.raise_for_status()

            data = resp.json()
            status = data.get("status")
            result: dict[str, Any] = {"status": status, "raw": data}

            # Status API shape (quickstart): top-level images[]
            images = data.get("images") or []
            video = data.get("video")
            # Some responses nest under payload
            nested = data.get("payload") or {}
            if not images and isinstance(nested, dict):
                images = nested.get("images") or []
                video = video or nested.get("video")

            if status == "completed":
                if images and isinstance(images, list) and isinstance(images[0], dict) and images[0].get("url"):
                    result["url"] = images[0]["url"]
                elif isinstance(video, dict) and video.get("url"):
                    result["url"] = video["url"]

            return result
