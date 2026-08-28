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
        self.api_key = getattr(settings, "SCRAPEGRAPH_API_KEY", None) or os.getenv("SCRAPEGRAPH_API_KEY")
        self.endpoint = "https://v2-api.scrapegraphai.com/api/extract"

    async def extract_landing_page(self, url: str) -> Dict[str, Any]:
        """
        Extracts marketing details from the landing page:
        headline, offer, positioning, cta.
        """
        if not url:
            return self._mock_extraction()

        if not self.api_key:
            logger.warning("SCRAPEGRAPH_API_KEY not set. Falling back to mocked landing page extraction.")
            await asyncio.sleep(0.5)
            return self._mock_extraction()

        prompt = (
            "Extract the main marketing headline, the core offer or value proposition, "
            "the brand's positioning or unique selling point, and the primary call to action (CTA). "
            "Return as JSON with keys: headline, offer, positioning, cta."
        )

        headers = {
            "SGAI-APIKEY": self.api_key.strip('"').strip("'"),
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "prompt": prompt
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                # ScrapeGraphAI v2 returns extracted data in the 'json' or 'result' field
                extracted = data.get("json") or data.get("result") or {}
                if isinstance(extracted, dict) and extracted:
                    return {
                        "headline": extracted.get("headline") or "Exclusive Online Offer",
                        "offer": extracted.get("offer") or "Special promotional pricing available now",
                        "positioning": extracted.get("positioning") or "Industry leading quality and performance",
                        "cta": extracted.get("cta") or "Shop Now"
                    }
                return self._mock_extraction()
        except Exception as e:
            logger.error(f"ScrapeGraphAI extraction failed for {url}: {e}")
            return self._mock_extraction()

    def _mock_extraction(self) -> Dict[str, Any]:
        return {
            "headline": "Unlock Your True Potential Today",
            "offer": "20% off your first subscription + free shipping",
            "positioning": "Premium quality ingredients backed by science",
            "cta": "Claim Your Offer"
        }
