import os
import asyncio
import httpx
import logging
from typing import List, Optional
from datetime import datetime, timezone
from app.services.scraping.base import ScraperProvider, RawCreative
from app.core.config import settings

logger = logging.getLogger(__name__)

class AdLibraryProvider(ScraperProvider):
    """
    Ad Discovery Provider supporting:
    - Meta Ad Library Graph API
    - Apify Facebook Ads Library Actor
    """

    def __init__(self, db=None, org_id: Optional[str] = None, user_id: Optional[str] = None):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id
        raw_meta = getattr(settings, "META_ACCESS_TOKEN", None) or os.getenv("META_ACCESS_TOKEN") or ""
        raw_apify = getattr(settings, "APIFY_API_TOKEN", None) or os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN") or ""
        
        self.meta_token = raw_meta.strip().strip('"\'')
        self.apify_token = raw_apify.strip().strip('"\'')
        self.meta_graph_version = "v21.0"

    async def search(self, query: str, max_records: int, filters: dict = None, progress_callback=None) -> List[RawCreative]:
        """
        Default combined search chain: Apify -> Meta Graph.
        """
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"
        if not query or not query.strip():
            return []

        cleaned_query = query.strip()
        country = (filters or {}).get("country", "ALL")

        # 1. Apify Facebook Ads Scraper (Primary ad scraper)
        if self.apify_token:
            creatives = await self.query_apify(cleaned_query, country, max_records, progress_callback=progress_callback)
            if creatives:
                logger.info(f"Retrieved {len(creatives)} creatives from Apify API")
                return creatives

        # 2. Meta Ad Library Graph API (if configured & approved)
        if self.meta_token:
            creatives = await self.query_meta_api(cleaned_query, country, max_records)
            if creatives:
                logger.info(f"Retrieved {len(creatives)} creatives from Meta Ad Library API")
                return creatives

        return []

    async def query_meta_api(self, query: str, country: str = "ALL", max_records: int = 15) -> List[RawCreative]:
        if not self.meta_token:
            logger.info("META_ACCESS_TOKEN not configured. Skipping Meta Graph API.")
            return []

        if country == "ALL" or not country:
            country_array = "['GB', 'US', 'DE', 'FR']"
        else:
            country_array = f"['{country}']"

        url = f"https://graph.facebook.com/{self.meta_graph_version}/ads_archive"
        params = {
            "access_token": self.meta_token,
            "ad_reached_countries": country_array,
            "search_terms": query,
            "ad_type": "ALL",
            "ad_active_status": "ALL",
            "fields": (
                "id,ad_creation_time,ad_delivery_start_time,ad_delivery_stop_time,"
                "ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,"
                "ad_creative_link_titles,ad_snapshot_url,page_id,page_name,publisher_platforms,"
                "impressions,spend"
            ),
            "limit": max_records
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    ads_data = data.get("data", [])
                    return self._parse_meta_ads(ads_data, query)
                else:
                    logger.warning(f"Meta Ad Library API returned status {resp.status_code}: {resp.text[:250]}")
                    return []
        except Exception as e:
            logger.error(f"Meta Ad Library API request failed: {e}")
            return []

    async def query_apify(self, query: str, country: str = "ALL", max_records: int = 15, progress_callback=None) -> List[RawCreative]:
        if not getattr(settings, "APIFY_ENABLED", False) or not self.apify_token:
            return []

        if progress_callback:
            await progress_callback(0, "Searching via Apify Facebook Ad Library actor...")

        url = f"https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        target_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country={country}&q={query}&search_type=keyword_unordered&media_type=all"
        payload = {
            "urls": [{"url": target_url}],
            "max_items": max_records
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in [200, 201]:
                    items = resp.json()
                    if isinstance(items, list) and items:
                        return self._parse_apify_ads(items, query)
                else:
                    logger.warning(f"Apify Actor returned status {resp.status_code}: {resp.text[:250]}")
        except Exception as e:
            logger.error(f"Apify scraper request failed: {e}")

        return []

    def _parse_meta_ads(self, ads_data: List[dict], fallback_brand: str) -> List[RawCreative]:
        creatives = []
        now = datetime.now(timezone.utc)

        for ad in ads_data:
            brand_name = ad.get("page_name") or fallback_brand.title()
            bodies = ad.get("ad_creative_bodies") or []
            body = bodies[0] if bodies else ""
            
            titles = ad.get("ad_creative_link_titles") or []
            headline = titles[0] if titles else (body[:60] if body else "")
            
            captions = ad.get("ad_creative_link_captions") or []
            landing_domain = captions[0] if captions else ""
            landing_url = f"https://{landing_domain}" if landing_domain else None

            platforms = ad.get("publisher_platforms") or ["meta"]
            platform = platforms[0].lower() if platforms else "meta"
            if platform in ["facebook", "instagram"]:
                platform = "meta"

            first_seen = ad.get("ad_delivery_start_time") or ad.get("ad_creation_time") or now.isoformat()
            last_seen = ad.get("ad_delivery_stop_time") or now.isoformat()
            
            days_active = 1
            try:
                dt_start = datetime.fromisoformat(first_seen.replace("Z", "+00:00").split("+")[0])
                days_active = max(1, (now.replace(tzinfo=None) - dt_start).days)
            except Exception:
                days_active = 1

            spend_info = ad.get("spend") or {}
            impressions_info = ad.get("impressions") or {}
            impressions_est = None
            if isinstance(impressions_info, dict) and impressions_info.get("upper_bound"):
                try:
                    impressions_est = int(impressions_info["upper_bound"])
                except Exception:
                    pass

            spend_band = None
            if isinstance(spend_info, dict) and spend_info.get("upper_bound"):
                try:
                    upper = int(spend_info["upper_bound"])
                    if upper < 1000:
                        spend_band = "low"
                    elif upper < 10000:
                        spend_band = "mid"
                    elif upper < 50000:
                        spend_band = "high"
                    else:
                        spend_band = "very_high"
                except Exception:
                    pass

            creatives.append(
                RawCreative(
                    platform=platform,
                    format="video" if "video" in body.lower() else "image",
                    brand_name=brand_name,
                    headline=headline,
                    body=body,
                    cta="Learn More",
                    landing_domain=landing_domain or None,
                    landing_url=landing_url,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    days_active=days_active,
                    variant_count=1,
                    impressions_est=impressions_est,
                    spend_band=spend_band,
                    data_source="meta_official",
                    is_estimated=False
                )
            )

        return creatives

    def _parse_apify_ads(self, items: List[dict], fallback_brand: str) -> List[RawCreative]:
        creatives = []
        now = datetime.now(timezone.utc)

        for item in items:
            brand_name = item.get("page_name") or item.get("pageName") or item.get("advertiser") or fallback_brand.title()
            body = item.get("ad_creative_bodies") or item.get("body") or item.get("text") or item.get("caption") or ""
            if isinstance(body, list):
                body = body[0] if body else ""
            
            title = item.get("ad_creative_link_titles") or item.get("title") or item.get("headline") or ""
            if isinstance(title, list):
                title = title[0] if title else ""

            landing_url = item.get("link_url") or item.get("url") or item.get("link")
            domain = None
            if landing_url and "://" in landing_url:
                try:
                    domain = landing_url.split("://")[1].split("/")[0]
                except Exception:
                    pass

            format_type = "video" if ("video" in str(item.get("media_type", "")).lower() or item.get("video_url")) else "image"
            
            creatives.append(
                RawCreative(
                    platform="meta",
                    format=format_type,
                    brand_name=brand_name,
                    headline=title or (body[:60] if body else ""),
                    body=body,
                    cta=item.get("cta_text") or item.get("cta") or "Learn More",
                    landing_domain=domain,
                    landing_url=landing_url,
                    first_seen=item.get("start_date") or now.isoformat(),
                    last_seen=item.get("end_date") or now.isoformat(),
                    days_active=item.get("days_active", 1),
                    variant_count=1,
                    impressions_est=None,
                    spend_band=None,
                    data_source="ad_library_scrape",
                    is_estimated=True
                )
            )

        return creatives
