import asyncio
import logging
import time
import re
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit
from datetime import datetime, timezone
from app.services.scraping.base import ScraperProvider, RawCreative
from app.services.scraping.search_filters import metapi_task_filters
from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

_PAGE_ID = re.compile(r"^\d{5,20}$")
_NAME_SUFFIXES = ("official", "inc", "llc", "ltd", "co", "store", "shop", "global")


def page_id_from_query(query: str) -> Optional[str]:
    """A Facebook page id, or the view_all_page_id of an Ad Library link."""
    text = (query or "").strip()
    if _PAGE_ID.match(text):
        return text
    lowered = text.lower()
    if "facebook.com" in lowered and "/ads/library" in lowered:
        try:
            values = parse_qs(urlsplit(text).query).get("view_all_page_id") or []
        except ValueError:
            return None
        value = (values[0] if values else "").strip()
        return value if _PAGE_ID.match(value) else None
    return None


def brand_term(query: str) -> str:
    """'Nike', 'nike.com', 'https://www.nike.com/x' -> 'nike'."""
    text = (query or "").strip().lower()
    if "://" in text:
        text = text.split("://", 1)[1].split("/", 1)[0]
    if text.startswith("www."):
        text = text[4:]
    if "." in text and " " not in text:
        text = text.split(".", 1)[0]
    return text


def _norm(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    while words and words[-1] in _NAME_SUFFIXES:
        words.pop()
    return "".join(words)


def pick_brand_page(items: list, brand: str) -> Optional[Tuple[str, str]]:
    """The advertiser page whose name is the brand (most ads wins), else None.

    Only exact name matches count (ignoring case, spaces, punctuation and a
    trailing word like "Official" or "Store"), so a reseller called
    "Nike Shoes PH" is never taken for Nike.
    """
    target = _norm(brand)
    if not target:
        return None
    counts: dict = {}
    for item in items or []:
        page_id = str(item.get("provider_page_id") or "").strip()
        name = str(item.get("provider_page_name") or "").strip()
        if page_id and _PAGE_ID.match(page_id) and _norm(name) == target:
            key = (page_id, name)
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _text(value) -> str:
    return str(value).strip() if value is not None else ""


def _texts(value) -> List[str]:
    if isinstance(value, str):
        value = [value]
    return [_text(v) for v in (value or []) if _text(v)]


MAX_COPY_VARIANTS = 20


def metapi_copy_variants(item: dict) -> List[dict]:
    """Every distinct copy variant of one ad, in Metapi's order.

    Metapi returns parallel lists (bodies, creative_link_titles,
    creative_link_descriptions); dynamic-creative ads carry several. Keeping
    only the first one hid the advertiser's copy testing.
    """
    bodies = _texts(item.get("bodies"))
    titles = _texts(item.get("creative_link_titles"))
    descriptions = _texts(item.get("creative_link_descriptions"))
    variants, seen = [], set()
    for i in range(max(len(bodies), len(titles), len(descriptions))):
        variant = {
            "body": bodies[i] if i < len(bodies) else "",
            "title": titles[i] if i < len(titles) else "",
            "description": descriptions[i] if i < len(descriptions) else "",
        }
        key = tuple(v.lower() for v in variant.values())
        if key in seen:
            continue
        seen.add(key)
        variants.append(variant)
        if len(variants) >= MAX_COPY_VARIANTS:
            break
    return variants


def _first_page_name(items: list) -> Optional[str]:
    for item in items or []:
        name = str(item.get("provider_page_name") or "").strip()
        if name:
            return name
    return None


class MetapiProvider(ScraperProvider):
    """
    Metapi Domain Trace Scraper Provider.
    Queries the Metapi API (https://api.metapi.io).
    """

    def __init__(self, db, org_id: str, user_id: str):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id
        self.metapi_api_key = env_secret(
            "METAPI_API_KEY",
            "METAPI_KEY",
            "METAPI_TOKEN",
            "Meta_Api",
            "META_API",
            "meta_api",
            fallback=getattr(settings, "METAPI_API_KEY", None),
        )

    async def search(self, query: str, max_records: int, filters: dict = None, progress_callback=None) -> List[RawCreative]:
        """Return a brand's own ads when the advertiser can be identified.

        * A Facebook page id, or an Ad Library link with ``view_all_page_id``,
          goes straight to Metapi's advertiser search.
        * Otherwise an exact-phrase keyword task finds the advertiser page whose
          name is the brand, and a second task fetches that page's ads (the
          keyword results alone are mostly look-alike sellers).
        * If no page matches, the keyword results are returned as before and
          the relevance filter decides what to keep.
        """
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"

        self.last_outcome = "failure"
        self.last_mode = "keyword"
        self.records_refused = False
        self.resolved_page_id = None
        self.resolved_page_name = None
        if not self.metapi_api_key:
            logger.warning("Metapi credentials missing. Skipping Metapi fallback.")
            return []

        if not query or not query.strip():
            self.last_outcome = "empty"
            return []

        if progress_callback:
            await progress_callback(0, "Initiating Domain Trace via Metapi...")

        try:
            page_id = page_id_from_query(query)
            if page_id:
                items = await self._run_task({"advertiser_id": page_id, "count": int(max_records), **metapi_task_filters(filters, advertiser=True)}, progress_callback)
                if items is None:
                    return []
                self.last_mode = "advertiser"
                self.resolved_page_id = page_id
                self.resolved_page_name = _first_page_name(items)
                return self._finish(items[:max_records], self.resolved_page_name or page_id)

            search_query = brand_term(query)
            resolve_count = max(int(max_records), int(getattr(settings, "METAPI_RESOLVE_COUNT", 30)))
            # count caps what Metapi collects (and bills as records). Exact
            # phrase cuts look-alike sellers that merely share a word.
            keyword_items = await self._run_task(
                {
                    "q": search_query,
                    "count": resolve_count,
                    **metapi_task_filters(filters, advertiser=False),
                    "search_type": "keyword_exact_phrase",
                },
                progress_callback,
            )
            if keyword_items is None:
                return []

            match = pick_brand_page(keyword_items, search_query)
            if match:
                from app.services import provider_budget

                refused = await provider_budget.reserve_provider_call("Metapi advertiser", org_id=self.org_id)
                if refused:
                    logger.warning("Metapi advertiser search skipped: %s", refused)
                else:
                    page_id, page_name = match
                    if progress_callback:
                        await progress_callback(0, "Found the advertiser page; loading its ads...")
                    advertiser_items = await self._run_task(
                        {"advertiser_id": page_id, "count": int(max_records), **metapi_task_filters(filters, advertiser=True)}, progress_callback
                    )
                    if advertiser_items:
                        self.last_mode = "advertiser"
                        self.resolved_page_id = page_id
                        self.resolved_page_name = page_name
                        return self._finish(advertiser_items[:max_records], page_name)

            return self._finish(keyword_items[:max_records], search_query)

        except Exception as e:
            logger.error(f"Metapi API request failed: {e}")
            return []

    def _finish(self, items: list, label: str) -> List[RawCreative]:
        parsed = self._parse_metapi_ads(items, label)
        self.last_outcome = "success" if parsed else "empty"
        return parsed

    async def _run_task(self, payload: dict, progress_callback=None) -> Optional[list]:
        """Create a Metapi task, wait for it, and return its ads; None on failure.

        Results are fetched only for a finished task; an unfinished one is a
        provider failure the job may retry, never an empty result.
        """
        from app.services import provider_budget
        from app.services.safe_fetch import safe_request_async

        # Metapi bills records: reserve this task's count first.
        if not await provider_budget.reserve_provider_records(
            "metapi", int(payload.get("count") or 50), int(settings.METAPI_MONTHLY_RECORD_BUDGET)
        ):
            self.records_refused = True
            return None

        headers = {
            "Authorization": "Bearer " + self.metapi_api_key.strip().strip('"').strip("'"),
            "Content-Type": "application/json",
        }
        hosts = {"api.metapi.io"}
        task_resp = await safe_request_async(
            "POST", "https://api.metapi.io/v1/tasks", json=payload, headers=headers,
            timeout=45.0, allowed_hosts=hosts,
        )
        if task_resp.status_code not in (200, 202):
            logger.warning("Metapi task creation failed: %s", task_resp.status_code)
            return None
        task_id = (task_resp.json() or {}).get("task_id")
        if not task_id:
            logger.warning("Metapi did not return a task_id")
            return None

        poll_budget_s = float(getattr(settings, "METAPI_POLL_TIMEOUT_S", 150))
        started = time.monotonic()
        delay = 1.5
        finished = False
        while time.monotonic() - started < poll_budget_s:
            await asyncio.sleep(delay)
            delay = min(delay * 1.4, 6.0)
            if progress_callback:
                await progress_callback(int(time.monotonic() - started), "Scraping live Meta Ad Library via Metapi...")
            status_resp = await safe_request_async(
                "GET", f"https://api.metapi.io/v1/tasks/{task_id}/status", headers=headers,
                timeout=45.0, allowed_hosts=hosts,
            )
            if status_resp.status_code == 200:
                status = (status_resp.json() or {}).get("status")
                if status == "succeeded":
                    finished = True
                    break
                if status in ("failed", "error", "timed_out", "aborted"):
                    logger.error("Metapi task failed: status=%s", status)
                    return None
        if not finished:
            logger.warning("Metapi task %s did not finish within %.0fs", task_id, poll_budget_s)
            return None

        results_resp = await safe_request_async(
            "GET", f"https://api.metapi.io/v1/tasks/{task_id}/results", headers=headers,
            timeout=45.0, allowed_hosts=hosts,
        )
        if results_resp.status_code != 200:
            logger.warning("Metapi results API returned status %s", results_resp.status_code)
            return None
        data = results_resp.json()
        if isinstance(data, dict):
            return list(data.get("data") or data.get("results") or [])
        return list(data) if isinstance(data, list) else []

    def _parse_metapi_ads(self, items: List[dict], domain: str) -> List[RawCreative]:
        creatives = []
        now = datetime.now(timezone.utc)
        brand_name = domain.split(".")[0].title()

        for item in items:
            page_name = item.get("provider_page_name") or brand_name
            
            video_hd = item.get("video_hd_url") or []
            video_sd = item.get("video_sd_url") or []
            video_previews = item.get("video_previews") or []
            orig_images = item.get("original_image_url") or []
            
            has_video = bool(video_hd or video_sd or video_previews)
            format_type = "video" if has_video else "image"
            
            bodies = item.get("bodies") or []
            body = bodies[0] if (bodies and len(bodies) > 0) else ""
            
            titles = item.get("creative_link_titles") or []
            captions = item.get("captions") or []
            
            # Extract first meaningful line from body copy as prime candidate for headline
            body_first_line = ""
            if body:
                lines = [l.strip() for l in body.splitlines() if l.strip()]
                if lines:
                    body_first_line = lines[0][:100]

            # Prioritize: 1) explicit link title, 2) ad copy first line, 3) caption/URL, 4) brand fallback
            if titles and len(titles) > 0 and titles[0].strip():
                headline = titles[0].strip()
            elif body_first_line:
                headline = body_first_line
            elif captions and len(captions) > 0 and captions[0].strip():
                headline = captions[0].strip()
            else:
                headline = None
            
            copy_variants = metapi_copy_variants(item)

            # link_url is Metapi's documented destination; query_params is a
            # legacy fallback.
            landing_url = item.get("link_url") or item.get("query_params")
            if not landing_url and captions and len(captions) > 0:
                cap = captions[0]
                landing_url = f"https://{cap}" if not cap.startswith("http") else cap
            
            cta = item.get("cta_text") or None
            
            start_date = item.get("creation_time") or item.get("delivery_start_time")
            end_date = item.get("delivery_stop_time")
            
            days_active = 1
            days_known = False
            if start_date:
                try:
                    dt_clean = start_date.replace("Z", "+00:00").split("+")[0]
                    dt_start = datetime.fromisoformat(dt_clean)
                    if dt_start.tzinfo is None:
                        dt_start = dt_start.replace(tzinfo=timezone.utc)
                    days_active = max(1, (now - dt_start.astimezone(timezone.utc)).days)
                    days_known = True
                except Exception:
                    days_active = 1

            # Pick best media URL
            media_url = None
            if video_hd and len(video_hd) > 0:
                media_url = video_hd[0]
            elif video_sd and len(video_sd) > 0:
                media_url = video_sd[0]
            elif orig_images and len(orig_images) > 0:
                media_url = orig_images[0]
            elif video_previews and len(video_previews) > 0:
                media_url = video_previews[0]

            thumbnail_url = video_previews[0] if (video_previews and len(video_previews) > 0) else (orig_images[0] if (orig_images and len(orig_images) > 0) else None)

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

            ad_id = _text(item.get("provider_id") or item.get("id") or item.get("ad_archive_id")) or None
            # snapshot_url is the documented field; the others are older names.
            # Live results (2026-11-08) carried none of them, so fall back to
            # the Ad Library's own link for the ad id.
            permalink = (
                item.get("snapshot_url") or item.get("ad_snapshot_url") or item.get("permalink")
                or (f"https://www.facebook.com/ads/library/?id={ad_id}" if ad_id and ad_id.isdigit() else None)
            )

            raw = RawCreative(
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
                    media_url=media_url,
                    thumbnail_url=thumbnail_url,
                    source_ad_id=ad_id,
                    permalink=permalink,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    provider="metapi",
                    raw={
                        "id": ad_id,
                        "permalink": permalink,
                        "copy_variants": copy_variants,
                        "countries": list(item.get("countries") or []),
                        "languages": list(item.get("languages") or []),
                        "page_id": _text(item.get("provider_page_id")) or None,
                        "metrics_observed": False,
                    },
                )
            creatives.append(raw)

        return creatives
