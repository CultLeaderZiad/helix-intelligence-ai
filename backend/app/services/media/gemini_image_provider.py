"""
Gemini Image Provider for Helix Intelligence.

Provides direct access to Google Gemini's image generation capability for
the 7-day free trial, enforcing server-side entitlement rules and saving
durable assets.
"""

import logging
from typing import Dict, Any, Optional, List
from app.services.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

class GeminiImageProvider:
    def __init__(self):
        self._provider = GeminiProvider()

    @property
    def is_configured(self) -> bool:
        return self._provider.is_configured

    @property
    def image_model(self) -> str:
        return self._provider.image_model

    async def generate_image(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "1:1",
        image_size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate image using Google Gemini.
        Returns dict with keys:
          - provider: "gemini"
          - model: <model_name>
          - media_type: "image"
          - mime_type: "image/png" | "image/jpeg"
          - data: bytes
          - metadata: dict
        """
        return await self._provider.generate_image(
            prompt=prompt,
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
