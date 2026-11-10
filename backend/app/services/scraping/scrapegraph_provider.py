import logging
from typing import Dict, Any
from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

class ScrapeGraphProvider:
    """
    Enriches a creative by extracting structured marketing data from its landing page
    using ScrapeGraphAI's v2 Extract API.
    """
    def __init__(self):
        raw_key = env_secret("SCRAPEGRAPH_API_KEY", fallback=getattr(settings, "SCRAPEGRAPH_API_KEY", None))
        self.api_key = raw_key
        self.endpoint = "https://v2-api.scrapegraphai.com/api/extract"

    async def extract_landing_page(self, url: str) -> Dict[str, Any]:
        """Extract landing-page fields. Failures are status=failure, never an empty dict."""
        if not url:
            return {"status": "skipped", "provider": "scrapegraph", "error": "missing_url"}

        if not self.api_key:
            logger.info("SCRAPEGRAPH_API_KEY not configured. Skipping landing page extraction.")
            return {"status": "skipped", "provider": "scrapegraph", "error": "not_configured"}

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
            from app.services.safe_fetch import safe_request_async
            response = await safe_request_async(
                "POST",
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=30.0,
                allowed_hosts={"v2-api.scrapegraphai.com"},
            )
            response.raise_for_status()
            data = response.json()
            extracted = data.get("json") or data.get("result") or {}
            if isinstance(extracted, dict) and any(extracted.get(key) for key in ("headline", "offer", "positioning", "cta")):
                return {
                    "status": "success",
                    "provider": "scrapegraph",
                    "headline": extracted.get("headline"),
                    "offer": extracted.get("offer"),
                    "positioning": extracted.get("positioning"),
                    "cta": extracted.get("cta"),
                    "error": None,
                }
            return {"status": "empty", "provider": "scrapegraph", "error": None}
        except Exception as e:
            logger.error("ScrapeGraphAI extraction failed for %s: %s", url, e)
            return {
                "status": "failure",
                "provider": "scrapegraph",
                "headline": None,
                "offer": None,
                "positioning": None,
                "cta": None,
                "error": str(e)[:300],
            }
