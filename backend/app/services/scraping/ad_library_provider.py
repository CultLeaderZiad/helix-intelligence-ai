import os
import asyncio
import httpx
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from app.services.scraping.base import ScraperProvider, RawCreative
from app.core.config import settings

logger = logging.getLogger(__name__)

class AdLibraryProvider(ScraperProvider):
    """
    Real Ad Discovery Provider with:
    1. Primary Path: Meta Ad Library Graph API (v21.0) using META_ACCESS_TOKEN
    2. Secondary Path: Bright Data Scraper / Dataset API using BRIGHTDATA_API_KEY
    3. Normalization into RawCreative schema
    """

    def __init__(self):
        self.meta_token = getattr(settings, "META_ACCESS_TOKEN", None) or os.getenv("META_ACCESS_TOKEN")
        self.brightdata_key = getattr(settings, "BRIGHTDATA_API_KEY", None) or os.getenv("BRIGHTDATA_API_KEY")
        self.meta_graph_version = "v21.0"

    async def search(self, query: str) -> List[RawCreative]:
        if not query or not query.strip():
            return []

        cleaned_query = query.strip()
        if cleaned_query == "*":
            # Search for broad generic term if wildcard
            cleaned_query = "brand"

        # 1. Try Meta Ad Library Graph API
        creatives = await self._query_meta_api(cleaned_query)
        if creatives:
            logger.info(f"Retrieved {len(creatives)} creatives from Meta Ad Library API")
            return creatives

        # 2. Try Bright Data Scraper / Dataset API
        creatives = await self._query_brightdata(cleaned_query)
        if creatives:
            logger.info(f"Retrieved {len(creatives)} creatives from Bright Data API")
            return creatives

        logger.info(f"Zero creatives found for query '{query}' across Meta and Bright Data sources.")
        return []

    async def _query_meta_api(self, query: str) -> List[RawCreative]:
        if not self.meta_token:
            logger.warning("META_ACCESS_TOKEN not configured.")
            return []

        url = f"https://graph.facebook.com/{self.meta_graph_version}/ads_archive"
        # Search multiple EU/UK and global markets
        params = {
            "access_token": self.meta_token.strip('"').strip("'"),
            "ad_reached_countries": "['GB', 'US', 'DE', 'FR']",
            "search_terms": query,
            "ad_type": "ALL",
            "ad_active_status": "ALL",
            "fields": (
                "id,ad_creation_time,ad_delivery_start_time,ad_delivery_stop_time,"
                "ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,"
                "ad_creative_link_titles,ad_snapshot_url,page_id,page_name,publisher_platforms,"
                "impressions,spend"
            ),
            "limit": 20
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

    def _parse_meta_ads(self, ads_data: List[dict], fallback_brand: str) -> List[RawCreative]:
        creatives = []
        now = datetime.utcnow()

        for ad in ads_data:
            ad_id = ad.get("id")
            brand_name = ad.get("page_name") or fallback_brand.title()
            
            # Extract bodies and titles
            bodies = ad.get("ad_creative_bodies") or []
            body = bodies[0] if bodies else ""
            
            titles = ad.get("ad_creative_link_titles") or []
            headline = titles[0] if titles else (body[:60] if body else f"{brand_name} Announcement")
            
            captions = ad.get("ad_creative_link_captions") or []
            landing_domain = captions[0] if captions else f"{brand_name.lower().replace(' ', '')}.com"
            landing_url = f"https://{landing_domain}" if landing_domain else None

            # Platforms
            platforms = ad.get("publisher_platforms") or ["meta"]
            platform = platforms[0].lower() if platforms else "meta"
            if platform in ["facebook", "instagram"]:
                platform = "meta"

            # Dates & duration
            first_seen = ad.get("ad_delivery_start_time") or ad.get("ad_creation_time") or now.isoformat() + "Z"
            last_seen = ad.get("ad_delivery_stop_time") or now.isoformat() + "Z"
            
            days_active = 1
            try:
                dt_start = datetime.fromisoformat(first_seen.replace("Z", "+00:00").split("+")[0])
                days_active = max(1, (now - dt_start).days)
            except Exception:
                days_active = 5

            # Spend & impression bands
            spend_info = ad.get("spend") or {}
            impressions_info = ad.get("impressions") or {}
            impressions_est = 25000
            if isinstance(impressions_info, dict) and impressions_info.get("upper_bound"):
                try:
                    impressions_est = int(impressions_info["upper_bound"])
                except Exception:
                    pass

            spend_band = "mid"
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
                    landing_domain=landing_domain,
                    landing_url=landing_url,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    days_active=days_active,
                    variant_count=1,
                    impressions_est=impressions_est,
                    spend_band=spend_band
                )
            )

        return creatives

    async def _query_brightdata(self, query: str) -> List[RawCreative]:
        if not self.brightdata_key:
            logger.warning("BRIGHTDATA_API_KEY not configured.")
            return []

        # Bright Data Web Scraper API for Facebook Ad Library / Social Ads
        # Format: POST https://api.brightdata.com/datasets/v3/scrape?format=json
        url = "https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_lkaxegm826bjpoo9m5&format=json"
        target_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query}"
        
        headers = {
            "Authorization": f"Bearer {self.brightdata_key.strip('\"').strip('\'')}",
            "Content-Type": "application/json"
        }
        payload = {"input": [{"url": target_url}]}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return self._parse_brightdata_ads(data, query)
                    elif isinstance(data, dict) and "results" in data:
                        return self._parse_brightdata_ads(data["results"], query)
                else:
                    logger.warning(f"Bright Data API returned status {resp.status_code}: {resp.text[:250]}")
                    return []
        except Exception as e:
            logger.error(f"Bright Data API request failed: {e}")
            return []

    def _parse_brightdata_ads(self, items: List[dict], fallback_brand: str) -> List[RawCreative]:
        creatives = []
        now = datetime.utcnow()

        for item in items:
            headline = item.get("headline") or item.get("title") or f"{fallback_brand.title()} Creative"
            body = item.get("body") or item.get("text") or item.get("post_text") or ""
            landing_url = item.get("link") or item.get("url") or f"https://{fallback_brand.lower()}.com"
            domain = fallback_brand.lower().replace(" ", "") + ".com"

            creatives.append(
                RawCreative(
                    platform="meta",
                    format="video" if item.get("video_url") else "image",
                    brand_name=fallback_brand.title(),
                    headline=headline,
                    body=body,
                    cta=item.get("cta") or "Learn More",
                    landing_domain=domain,
                    landing_url=landing_url,
                    first_seen=now.isoformat() + "Z",
                    last_seen=now.isoformat() + "Z",
                    days_active=item.get("days_active", 7),
                    variant_count=1,
                    impressions_est=item.get("impressions", 50000),
                    spend_band="mid"
                )
            )

        return creatives
