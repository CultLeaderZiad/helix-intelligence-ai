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

    async def search(self, query: str, progress_callback=None) -> List[RawCreative]:
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

        # 2. Try Bright Data Scraper / Dataset API (Async Trigger -> Poll Snapshot)
        creatives = await self._query_brightdata(cleaned_query, progress_callback=progress_callback)
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

    async def _query_brightdata(self, query: str, progress_callback=None) -> List[RawCreative]:
        if not self.brightdata_key:
            logger.warning("BRIGHTDATA_API_KEY not configured.")
            return []

        # Bright Data Facebook Ads Library Dataset Trigger (Async Pattern)
        url = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_lkaxegm826bjpoo9m5&format=json"
        target_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query}&search_type=keyword_unordered&media_type=all"
        
        headers = {
            "Authorization": f"Bearer {self.brightdata_key.strip('\"').strip('\'')}",
            "Content-Type": "application/json"
        }
        payload = [{"url": target_url}]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Bright Data trigger returned status {resp.status_code}: {resp.text[:250]}")
                    return []
                
                trigger_data = resp.json()
                snapshot_id = trigger_data.get("snapshot_id")
                if not snapshot_id:
                    logger.warning(f"Bright Data trigger response missing snapshot_id: {trigger_data}")
                    return []
                
                logger.info(f"Bright Data snapshot triggered: {snapshot_id}. Polling progress (up to 5m)...")
                
                # Poll snapshot progress every 12s for up to 5 minutes
                start_time = asyncio.get_event_loop().time()
                max_duration = 300.0
                poll_interval = 12.0

                while (asyncio.get_event_loop().time() - start_time) < max_duration:
                    await asyncio.sleep(poll_interval)
                    elapsed_s = int(asyncio.get_event_loop().time() - start_time)
                    
                    if progress_callback:
                        await progress_callback(elapsed_s, f"Waiting on Bright Data snapshot ({elapsed_s}s elapsed)")
                        
                    prog_resp = await client.get(
                        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                        headers=headers
                    )
                    if prog_resp.status_code == 200:
                        prog_data = prog_resp.json()
                        status = prog_data.get("status")
                        logger.info(f"Bright Data snapshot {snapshot_id} status: {status} ({elapsed_s}s)")
                        
                        if status == "ready":
                            snap_resp = await client.get(
                                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
                                headers=headers,
                                timeout=60.0
                            )
                            if snap_resp.status_code == 200:
                                items = snap_resp.json()
                                if isinstance(items, list):
                                    return self._parse_brightdata_ads(items, query)
                                elif isinstance(items, dict) and "results" in items:
                                    return self._parse_brightdata_ads(items["results"], query)
                            break
                        elif status == "failed":
                            logger.error(f"Bright Data snapshot {snapshot_id} failed: {prog_data}")
                            break
        except Exception as e:
            logger.error(f"Bright Data API async poll failed: {e}")
            return []

        return []

    def _parse_brightdata_ads(self, items: List[dict], fallback_brand: str) -> List[RawCreative]:
        creatives = []
        now = datetime.utcnow()

        for item in items:
            brand_name = (
                item.get("page_name") or 
                item.get("advertiser_name") or 
                item.get("brand") or 
                fallback_brand.title()
            )
            headline = (
                item.get("headline") or 
                item.get("title") or 
                item.get("ad_creative_link_titles", [""])[0] if isinstance(item.get("ad_creative_link_titles"), list) and item.get("ad_creative_link_titles") else None or
                f"{brand_name} Announcement"
            )
            body = (
                item.get("body") or 
                item.get("text") or 
                item.get("post_text") or 
                item.get("caption") or 
                (item.get("ad_creative_bodies", [""])[0] if isinstance(item.get("ad_creative_bodies"), list) and item.get("ad_creative_bodies") else "") or
                ""
            )
            landing_url = (
                item.get("link") or 
                item.get("url") or 
                item.get("landing_page_url") or 
                f"https://{fallback_brand.lower().replace(' ', '')}.com"
            )
            domain = fallback_brand.lower().replace(" ", "") + ".com"
            if landing_url and "://" in landing_url:
                try:
                    domain = landing_url.split("://")[1].split("/")[0]
                except Exception:
                    pass

            format_type = "video" if (item.get("video_url") or "video" in str(item.get("media_type", "")).lower()) else "image"
            
            impressions_est = 50000
            if item.get("impressions"):
                try:
                    impressions_est = int(item["impressions"])
                except Exception:
                    pass

            creatives.append(
                RawCreative(
                    platform="meta",
                    format=format_type,
                    brand_name=brand_name,
                    headline=headline,
                    body=body,
                    cta=item.get("cta") or "Learn More",
                    landing_domain=domain,
                    landing_url=landing_url,
                    first_seen=item.get("start_date") or now.isoformat() + "Z",
                    last_seen=item.get("end_date") or now.isoformat() + "Z",
                    days_active=item.get("days_active", 7),
                    variant_count=1,
                    impressions_est=impressions_est,
                    spend_band=item.get("spend_band", "mid")
                )
            )

        return creatives
