import os
import asyncio
import httpx
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class ScrapeGraphProvider:
    """
    Enriches a creative by extracting structured marketing data from its landing page
    using ScrapeGraphAI's v2 Extract API.
    """
    def __init__(self):
        raw_key = getattr(settings, "SCRAPEGRAPH_API_KEY", None) or os.getenv("SCRAPEGRAPH_API_KEY") or ""
        self.api_key = raw_key.strip().strip('"\'')
        self.endpoint = "https://v2-api.scrapegraphai.com/api/extract"

    async def extract_landing_page(self, url: str) -> Dict[str, Any]:
        """
        Extracts marketing details from the landing page:
        headline, offer, positioning, cta.
        Returns empty dict if URL is invalid, API key missing, or extraction fails.
        """
        if not url:
            return {}

        if not self.api_key:
            logger.info("SCRAPEGRAPH_API_KEY not configured. Skipping landing page extraction.")
            return {}

        prompt = (
            "Extract the main marketing headline, the core offer or value proposition, "
            "the brand's positioning or unique selling point, and the primary call to action (CTA). "
            "Return as JSON with keys: headline, offer, positioning, cta."
        )

        headers = {
            "SGAI-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "prompt": prompt
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                extracted = data.get("json") or data.get("result") or {}
                if isinstance(extracted, dict) and extracted:
                    return {
                        "headline": extracted.get("headline"),
                        "offer": extracted.get("offer"),
                        "positioning": extracted.get("positioning"),
                        "cta": extracted.get("cta")
                    }
                return {}
        except Exception as e:
            logger.error(f"ScrapeGraphAI extraction failed for {url}: {e}")
            return {}
