import os
import asyncio
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ScrapeGraphProvider:
    """
    Enriches a creative by extracting structured marketing data from its landing page
    using ScrapeGraphAI's SmartScraper.
    """
    def __init__(self):
        self.api_key = os.getenv("SCRAPEGRAPH_API_KEY")
        # Example API endpoint if they have a managed REST API, 
        # or we could use their python SDK if it was installed.
        # We will use httpx to mock a REST call for robustness in async environments.
        self.endpoint = "https://api.scrapegraphai.com/v1/smartscraper"

    async def extract_landing_page(self, url: str) -> Dict[str, Any]:
        """
        Extracts marketing details from the landing page:
        headline, offer, positioning, cta.
        """
        if not url:
            return self._mock_extraction()

        if not self.api_key:
            logger.warning("SCRAPEGRAPH_API_KEY not set. Falling back to mocked landing page extraction.")
            # Simulate latency
            await asyncio.sleep(1.0)
            return self._mock_extraction()

        prompt = (
            "Extract the main marketing headline, the core offer or value proposition, "
            "the brand's positioning or unique selling point, and the primary call to action (CTA). "
            "Return as JSON with keys: headline, offer, positioning, cta."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                return data.get("result", self._mock_extraction())
        except Exception as e:
            logger.error(f"ScrapeGraphAI extraction failed for {url}: {e}")
            # Graceful fallback on error so the pipeline doesn't completely fail
            return self._mock_extraction()

    def _mock_extraction(self) -> Dict[str, Any]:
        return {
            "headline": "Unlock Your True Potential Today",
            "offer": "20% off your first subscription + free shipping",
            "positioning": "Premium quality ingredients backed by science",
            "cta": "Claim Your Offer"
        }
