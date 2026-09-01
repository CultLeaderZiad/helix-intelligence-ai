import os
import asyncio
import httpx
import logging
from typing import List
from datetime import datetime
from app.services.scraping.base import ScraperProvider, RawCreative
from app.core.config import settings

logger = logging.getLogger(__name__)

class MetapiProvider(ScraperProvider):
    """
    Metapi Domain Trace Scraper Provider.
    Queries the Metapi API (https://api.metapi.io).
    """

    def __init__(self, db, org_id: str, user_id: str):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id
        self.metapi_api_key = getattr(settings, "METAPI_API_KEY", None) or os.getenv("METAPI_API_KEY")

    async def search(self, query: str, max_records: int, filters: dict = None, progress_callback=None) -> List[RawCreative]:
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"
        
        if not self.metapi_api_key:
            logger.warning("Metapi credentials missing. Skipping Metapi fallback.")
            return []
            
        if not query or not query.strip():
            return []

        clean_brand = query.strip().lower()
        if clean_brand == "*":
            clean_brand = "brand"
            
        domain = clean_brand
        if "://" in domain:
            try:
                domain = domain.split("://")[1].split("/")[0]
            except:
                pass
        
        # Metapi uses a general search query. We'll search the clean brand name without .com if possible.
        search_query = domain.split(".")[0] if "." in domain else domain

        headers = {
            "Authorization": "Bearer " + self.metapi_api_key.strip().strip('"').strip("'"),
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": search_query,
            "country": "ALL"
        }

        if progress_callback:
            await progress_callback(0, "Initiating Domain Trace via Metapi...")

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                # 1. Create Task
                task_resp = await client.post("https://api.metapi.io/v1/tasks", json=payload, headers=headers)
                if task_resp.status_code != 202 and task_resp.status_code != 200:
                    logger.warning(f"Metapi task creation failed: {task_resp.status_code} {task_resp.text[:250]}")
                    return []
                
                task_data = task_resp.json()
                task_id = task_data.get("task_id")
                if not task_id:
                    logger.warning(f"Metapi did not return a task_id: {task_data}")
                    return []

                # 2. Poll Task Status
                max_attempts = 15
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)
                    if progress_callback:
                        await progress_callback(attempt * 2, "Waiting for Metapi trace results...")
                        
                    status_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/status", headers=headers)
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        status = status_data.get("status")
                        if status == "succeeded":
                            break
                        elif status == "failed":
                            logger.error(f"Metapi task failed: {status_data}")
                            return []
                    
                # 3. Get Results
                results_resp = await client.get(f"https://api.metapi.io/v1/tasks/{task_id}/results", headers=headers)
                if results_resp.status_code == 200:
                    results_data = results_resp.json()
                    results = results_data.get("data", [])
                    
                    if len(results) > max_records:
                        results = results[:max_records]
                        
                    return self._parse_metapi_ads(results, domain)
                else:
                    logger.warning(f"Metapi results API returned status {results_resp.status_code}: {results_resp.text[:250]}")
                    return []
                    
        except Exception as e:
            logger.error(f"Metapi API request failed: {e}")
            return []

    def _parse_metapi_ads(self, items: List[dict], domain: str) -> List[RawCreative]:
        creatives = []
        now = datetime.utcnow()
        brand_name = domain.split(".")[0].title()

        for item in items:
            page_name = item.get("provider_page_name") or brand_name
            
            video_hd = item.get("video_hd_url", [])
            video_sd = item.get("video_sd_url", [])
            has_video = bool(video_hd or video_sd)
            format_type = "video" if has_video else "image"
            
            bodies = item.get("bodies", [])
            body = bodies[0] if bodies else ""
            
            titles = item.get("creative_link_titles", [])
            title = titles[0] if titles else ""
            
            headline = title or (body[:60] if body else "")
            
            landing_url = item.get("query_params")
            
            cta = item.get("cta_text") or "Learn More"
            
            start_date = item.get("creation_time") or item.get("delivery_start_time") or now.isoformat()
            end_date = item.get("delivery_stop_time") or now.isoformat()
            
            days_active = 1
            try:
                dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00").split("+")[0])
                days_active = max(1, (now.replace(tzinfo=None) - dt_start).days)
            except Exception:
                days_active = 1

            creatives.append(
                RawCreative(
                    platform="meta",
                    format=format_type,
                    brand_name=page_name,
                    headline=headline,
                    body=body,
                    cta=cta,
                    landing_domain=domain,
                    landing_url=landing_url,
                    first_seen=start_date,
                    last_seen=end_date,
                    days_active=days_active,
                    variant_count=1,
                    impressions_est=None,
                    spend_band=None,
                    data_source="ad_library_scrape",
                    is_estimated=True
                )
            )

        return creatives
