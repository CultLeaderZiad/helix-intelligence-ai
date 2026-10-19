import os
import asyncio
import logging
from typing import List
from datetime import datetime, timezone
from app.services.scraping.base import ProviderFailure, ScraperProvider, RawCreative
from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

class AdyntelProvider(ScraperProvider):
    """
    Adyntel Fallback Scraper Provider.
    Queries the Adyntel Meta Ads endpoint (https://api.adyntel.com/facebook).
    """

    def __init__(self, db, org_id: str, user_id: str):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id
        self.adyntel_api_key = env_secret(
            "ADYNTEL_API_KEY",
            fallback=getattr(settings, "ADYNTEL_API_KEY", None),
        )
        self.adyntel_email = env_secret(
            "ADYNTEL_EMAIL",
            fallback=getattr(settings, "ADYNTEL_EMAIL", None),
        )

    async def search(self, query: str, max_records: int, filters: dict = None, progress_callback=None) -> List[RawCreative]:
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"
        
        self.last_outcome = "skipped"
        if not self.adyntel_api_key or not self.adyntel_email:
            logger.warning("Adyntel credentials missing. Skipping Adyntel fallback.")
            return []

        if not query or not query.strip():
            self.last_outcome = "empty"
            return []

        # Adyntel answers company_domain lookups only. Keyword queries used
        # to be mangled into "{query}.com" here — refuse them outright.
        from app.services.scraping.ad_library_provider import is_domain_shaped
        if not is_domain_shaped(query):
            logger.info("Adyntel skipped: query='%s' is not domain-shaped", query.strip())
            return []

        clean_brand = query.strip().lower()
        if clean_brand == "*":
            clean_brand = "brand.com"
            
        domain = clean_brand
        if "://" in domain:
            try:
                domain = domain.split("://")[1].split("/")[0]
            except:
                pass
        if "." not in domain:
            domain = f"{domain.replace(' ', '')}.com"

        url = "https://api.adyntel.com/facebook"
        payload = {
            "api_key": self.adyntel_api_key.strip('"').strip("'"),
            "email": self.adyntel_email.strip('"').strip("'"),
            "company_domain": domain,
            "active_status": "active"
        }

        if progress_callback:
            await progress_callback(0, "Searching via Adyntel fallback...")

        try:
            # NO RETRIES allowed on this paid API call.
            # Host allowlist keeps the Adyntel key on api.adyntel.com; the fetch is still pinned.
            from app.services.safe_fetch import safe_request_async
            resp = await safe_request_async(
                "POST", url, json=payload, timeout=45.0, allowed_hosts={"api.adyntel.com"}
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                # Limit the results array locally as an extra safety measure
                if len(results) > max_records:
                    results = results[:max_records]

                parsed = self._parse_adyntel_ads(results, domain)
                self.last_outcome = "success" if parsed else "empty"
                return parsed
            self.last_outcome = "failure"
            raise ProviderFailure(
                "adyntel",
                f"Adyntel HTTP {resp.status_code}",
                http_status=resp.status_code,
            )
        except ProviderFailure:
            raise
        except Exception as e:
            self.last_outcome = "failure"
            logger.error(f"Adyntel API request failed: {e}")
            raise ProviderFailure("adyntel", f"Adyntel request failed: {e}") from e

    def _parse_adyntel_ads(self, items: List[dict], domain: str) -> List[RawCreative]:
        creatives = []
        now = datetime.utcnow()
        brand_name = domain.split(".")[0].title()

        for item in items:
            # Extract basic data
            page_id = item.get("page_id", "")
            page_name = item.get("page_name") or brand_name
            
            snapshot = item.get("snapshot", {})
            media_types = item.get("media_types", [])
            format_type = "video" if "video" in media_types else "image"
            
            body_obj = snapshot.get("body") or {}
            body = body_obj.get("text", "")
            
            # Adyntel sometimes puts title in cards
            title = snapshot.get("title")
            if title == "{{product.name}}" and snapshot.get("cards"):
                title = snapshot["cards"][0].get("title")
            
            headline = title or (body[:60] if body else "")
            
            # Check cards for link_url or use snapshot.link_url
            link_url = snapshot.get("link_url")
            if snapshot.get("cards") and snapshot["cards"][0].get("link_url"):
                link_url = snapshot["cards"][0].get("link_url")
                
            landing_url = link_url
            
            # Check cards for cta_text
            cta = snapshot.get("cta_text")
            if not cta and snapshot.get("cards"):
                cta = snapshot["cards"][0].get("cta_text")
            if not cta:
                cta = snapshot.get("cta_type") or None
            
            start_date = item.get("start_date_string")
            end_date = item.get("end_date_string")
            
            days_active = 1
            days_known = False
            if start_date:
                try:
                    dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00").split("+")[0])
                    days_active = max(1, (now.replace(tzinfo=None) - dt_start).days)
                    days_known = True
                except Exception:
                    days_known = False

            landing_domain = None
            if landing_url:
                try:
                    from urllib.parse import urlparse
                    netloc = urlparse(landing_url).netloc
                    if netloc:
                        landing_domain = netloc.lower().replace("www.", "")
                except Exception:
                    pass
            if not landing_domain and domain and "." in domain and " " not in domain:
                landing_domain = domain.lower().replace("www.", "")

            fetched_at = datetime.now(timezone.utc).isoformat()
            creatives.append(
                RawCreative(
                    platform="meta",
                    format=format_type,
                    brand_name=page_name,
                    headline=headline,
                    body=body,
                    cta=cta,
                    landing_domain=landing_domain,
                    landing_url=landing_url,
                    first_seen=start_date,
                    last_seen=end_date,
                    days_active=days_active,
                    days_known=days_known,
                    variant_count=1,
                    impressions_est=None,
                    spend_band=None,
                    data_source="ad_library_scrape",
                    is_estimated=True,
                    source_ad_id=item.get("ad_archive_id") or item.get("id") or None,
                    permalink=item.get("ad_snapshot_url") or None,
                    fetched_at=fetched_at,
                    provider="adyntel",
                    raw={
                        "ad_archive_id": item.get("ad_archive_id") or item.get("id"),
                        "page_id": page_id or None,
                        "permalink": item.get("ad_snapshot_url"),
                    },
                )
            )

        return creatives
