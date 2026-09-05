import os
import re
import asyncio
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.services.scraping.base import ScraperProvider, RawCreative
from app.services.scraping.metapi_provider import MetapiProvider
from app.services.scraping.adyntel_provider import AdyntelProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

# ==============================================================================
# CANONICAL AD DISCOVERY PROVIDER CHAIN (Single Source of Truth)
# Order:
# 1. Metapi (Primary: fast, live Meta Ad Library search)
# 2. Adyntel (Secondary: company/domain trace fallback)
# 3. Meta Official Graph API (Tertiary: official ads_archive endpoint with app access token)
# 4. Apify Facebook Ad Library Actor (Last resort: actor scraper kept for fallback)
# ==============================================================================
DISCOVERY_PROVIDER_CHAIN = [
    "metapi",
    "adyntel",
    "meta_official",
    "apify",
]

# A plausible domain: dot-separated labels ending in an alpha TLD. This is
# the ONLY query shape Adyntel's company_domain endpoint can answer —
# anything else used to be blindly turned into "{query}.com" and was
# guaranteed to fail (while still spending a paid API call).
_DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$", re.IGNORECASE)


def is_domain_shaped(query: str) -> bool:
    """True when the query is (or starts with) an actual domain —
    e.g. 'nike.com', 'https://nike.com/shoes', 'www.nike.co.uk'."""
    candidate = (query or "").strip().lower()
    if "://" in candidate:
        candidate = candidate.split("://", 1)[1]
    candidate = candidate.split("/", 1)[0].split(":", 1)[0].strip()
    if candidate.startswith("www."):
        candidate = candidate[4:]
    return " " not in candidate and bool(_DOMAIN_RE.match(candidate))


class AdLibraryProvider(ScraperProvider):
    """
    Unified Ad Discovery Provider and Single Source of Truth for ad search.
    Orchestrates the fallback chain: Metapi -> Adyntel -> Meta Official API -> Apify.
    """

    def __init__(self, db=None, org_id: Optional[str] = None, user_id: Optional[str] = None):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id

        # Sub-providers
        self.metapi_provider = MetapiProvider(db, str(org_id) if org_id else "", str(user_id) if user_id else "")
        self.adyntel_provider = AdyntelProvider(db, str(org_id) if org_id else "", str(user_id) if user_id else "")

        raw_meta = getattr(settings, "META_ACCESS_TOKEN", None) or os.getenv("META_ACCESS_TOKEN") or ""
        raw_apify = getattr(settings, "APIFY_API_TOKEN", None) or os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN") or ""
        
        self.meta_token = raw_meta.strip().strip('"\'')
        self.apify_token = raw_apify.strip().strip('"\'')
        self.meta_graph_version = "v21.0"

        # Execution tracking
        self.last_provider_used: str = "none"
        self.sources_tried: List[str] = []
        # Per-source outcome ledger for one search(): name -> {"status", "detail"}.
        #   answered  -> the API replied (whether or not it had rows for us)
        #   error     -> the API rejected us or the transport failed
        #   skipped   -> we deliberately did not call it (missing creds, query shape)
        # Without this, every upstream outage looked identical to "brand has no
        # ads": both paths returned [] and the job was reported as a clean
        # zero-result search while still charging the user's credits.
        self.source_outcomes: Dict[str, dict] = {}

    # ------------------------------------------------------------------ ledger
    def _record(self, source: str, status: str, detail: str = "") -> None:
        """Log one source's outcome. An 'error' is never overwritten by a
        later 'answered' with no rows — the reason matters more than the count."""
        existing = self.source_outcomes.get(source, {})
        if existing.get("status") == "error" and status != "error":
            return
        self.source_outcomes[source] = {"status": status, "detail": (detail or "")[:300]}

    @property
    def any_source_answered(self) -> bool:
        """True when at least one provider actually responded. This is the
        difference between 'we searched and found nothing' and 'we could not
        search at all'."""
        return any(o.get("status") == "answered" for o in self.source_outcomes.values())

    @property
    def failure_reasons(self) -> List[str]:
        return [
            f"{name}: {o.get('detail') or 'request failed'}"
            for name, o in self.source_outcomes.items()
            if o.get("status") == "error"
        ]

    def _record_empty(self, source: str, sub_error: Optional[str] = None) -> None:
        """A source came back with no rows. Two very different causes hide here:
        the provider told us the upstream call failed (error), versus it
        searched successfully and genuinely matched nothing (answered)."""
        if sub_error:
            self._record(source, "error", str(sub_error))
        else:
            self._record(source, "answered", "search completed, 0 matching ads")

    async def search(
        self,
        query: str,
        max_records: int = 15,
        filters: Optional[dict] = None,
        progress_callback=None
    ) -> List[RawCreative]:
        """
        Executes the canonical provider chain in order:
        1. Metapi (Primary)
        2. Adyntel (Secondary)
        3. Meta Official Graph API (Tertiary)
        4. Apify (Last Resort)

        Returns the first non-empty result set. Each source visited is recorded
        in self.source_outcomes, so a caller can tell "searched, found nothing"
        apart from "could not search" — the first is a real result, the second
        must never be billed.
        """
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"
        if not query or not query.strip():
            return []

        cleaned_query = query.strip()
        country = (filters or {}).get("country", "ALL")
        self.sources_tried = []
        self.source_outcomes = {}
        self.last_provider_used = "none"

        # ----------------------------------------------------------------------
        # 1. METAPI (Primary: Live Meta Ad Library search)
        # ----------------------------------------------------------------------
        if not self.metapi_provider.metapi_api_key:
            self._record("Metapi", "skipped", "METAPI_API_KEY not configured")
        else:
            self.sources_tried.append("Metapi")
            logger.info(f"[AdDiscovery] Attempting primary provider: Metapi for query='{cleaned_query}'")
            try:
                creatives = await self.metapi_provider.search(
                    cleaned_query,
                    max_records=max_records,
                    filters=filters,
                    progress_callback=progress_callback
                )
                if creatives:
                    self._record("Metapi", "answered", f"{len(creatives)} creatives")
                    self.last_provider_used = "metapi"
                    logger.info(f"[AdDiscovery] Metapi succeeded with {len(creatives)} creatives")
                    return creatives
                self._record_empty("Metapi", getattr(self.metapi_provider, "last_error", None))
            except Exception as e:
                self._record("Metapi", "error", str(e))
                logger.warning(f"[AdDiscovery] Metapi search failed: {e}, falling back to Adyntel")

        # ----------------------------------------------------------------------
        # 2. ADYNTEL (Secondary: Domain/company trace fallback — domains only)
        # ----------------------------------------------------------------------
        if not (self.adyntel_provider.adyntel_api_key and self.adyntel_provider.adyntel_email):
            self._record("Adyntel", "skipped", "ADYNTEL_API_KEY / ADYNTEL_EMAIL not configured")
        elif not is_domain_shaped(cleaned_query):
            # Keyword queries are not domains: appending ".com" here produced
            # garbage like "mosalah.com" and a guaranteed-wasted paid call.
            self._record("Adyntel", "skipped", "query is not domain-shaped (company_domain endpoint only)")
            logger.info(
                "[AdDiscovery] Skipping Adyntel for keyword query='%s' (domain-shaped queries only)",
                cleaned_query,
            )
        else:
            self.sources_tried.append("Adyntel")
            logger.info(f"[AdDiscovery] Attempting secondary provider: Adyntel for query='{cleaned_query}'")
            try:
                creatives = await self.adyntel_provider.search(
                    cleaned_query,
                    max_records=max_records,
                    filters=filters,
                    progress_callback=progress_callback
                )
                if creatives:
                    self._record("Adyntel", "answered", f"{len(creatives)} creatives")
                    self.last_provider_used = "adyntel"
                    logger.info(f"[AdDiscovery] Adyntel succeeded with {len(creatives)} creatives")
                    return creatives
                self._record_empty("Adyntel", getattr(self.adyntel_provider, "last_error", None))
            except Exception as e:
                self._record("Adyntel", "error", str(e))
                logger.warning(f"[AdDiscovery] Adyntel search failed: {e}, falling back to Meta Official API")

        # ----------------------------------------------------------------------
        # 3. META OFFICIAL GRAPH API (Tertiary: Official ads_archive endpoint)
        # ----------------------------------------------------------------------
        if not self.meta_token:
            self._record("Meta Graph API", "skipped", "META_ACCESS_TOKEN not configured")
        else:
            self.sources_tried.append("Meta Graph API")
            logger.info(f"[AdDiscovery] Attempting tertiary provider: Meta Graph API for query='{cleaned_query}'")
            try:
                if progress_callback:
                    await progress_callback(0, "Querying Meta Graph API (Official)...")
                creatives = await self.query_meta_api(cleaned_query, country=country, max_records=max_records)
                if creatives:
                    self._record("Meta Graph API", "answered", f"{len(creatives)} creatives")
                    self.last_provider_used = "meta_graph"
                    logger.info(f"[AdDiscovery] Meta Graph API succeeded with {len(creatives)} creatives")
                    return creatives
                # query_meta_api records the concrete rejection (status + subcode)
                # itself; a bare empty list therefore means "answered, no matches".
                self._record_empty("Meta Graph API")
            except Exception as e:
                self._record("Meta Graph API", "error", str(e))
                logger.warning(f"[AdDiscovery] Meta Graph API request failed: {e}, falling back to Apify")

        # ----------------------------------------------------------------------
        # 4. APIFY FACEBOOK AD LIBRARY ACTOR (Last Resort: actor scraper)
        # ----------------------------------------------------------------------
        if not self.apify_token:
            self._record("Apify (Facebook Ad Library)", "skipped", "APIFY_API_TOKEN not configured")
        elif not getattr(settings, "APIFY_ENABLED", False):
            self._record("Apify (Facebook Ad Library)", "skipped", "APIFY_ENABLED=false")
        else:
            self.sources_tried.append("Apify (Facebook Ad Library)")
            logger.info(f"[AdDiscovery] Attempting last-resort provider: Apify for query='{cleaned_query}'")
            try:
                creatives = await self.query_apify(
                    cleaned_query,
                    country=country,
                    max_records=max_records,
                    progress_callback=progress_callback
                )
                if creatives:
                    self._record("Apify (Facebook Ad Library)", "answered", f"{len(creatives)} creatives")
                    self.last_provider_used = "apify"
                    logger.info(f"[AdDiscovery] Apify succeeded with {len(creatives)} creatives")
                    return creatives
                self._record_empty("Apify (Facebook Ad Library)")
            except Exception as e:
                self._record("Apify (Facebook Ad Library)", "error", str(e))
                logger.warning(f"[AdDiscovery] Apify search failed: {e}")

        logger.info(
            f"[AdDiscovery] All providers exhausted for query='{cleaned_query}'. "
            f"Tried: {self.sources_tried}; outcomes: {self.source_outcomes}"
        )
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
                    body = resp.text[:250]
                    logger.warning(f"Meta Ad Library API returned status {resp.status_code}: {body}")
                    self._record("Meta Graph API", "error", self._classify_meta_error(resp, body))
                    return []
        except Exception as e:
            logger.error(f"Meta Ad Library API request failed: {e}")
            self._record("Meta Graph API", "error", f"request failed: {e}")
            return []

    @staticmethod
    def _classify_meta_error(resp, body: str) -> str:
        """Turn a Graph API rejection into the reason an operator can act on.

        Subcode 2332002 in particular is not a query problem — it means the
        app has not been granted ads_archive access, so no query will ever
        work until the App Review grant lands. Saying 'no ads found' would be
        a lie we then bill the customer for.
        """
        code = subcode = None
        try:
            err = (resp.json() or {}).get("error") or {}
            code = err.get("code")
            subcode = err.get("error_subcode")
        except Exception:
            pass
        if subcode == 2332002 or "2332002" in body:
            return (
                "HTTP 400 subcode 2332002 — app is not authorized for ads_archive "
                "(Meta Ad Library API access not granted)"
            )
        if code in (190, 463, 460) or "OAuthException" in body:
            return f"HTTP {resp.status_code} — access token invalid or expired"
        return f"HTTP {resp.status_code}: {body[:120]}"

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
                    return []
                else:
                    body = resp.text[:250]
                    logger.warning(f"Apify Actor returned status {resp.status_code}: {body}")
                    if resp.status_code == 402 or "not-enough-usage" in body:
                        detail = (
                            "HTTP 402 — Apify account has no remaining usage credit "
                            "(actor cannot run until the plan is funded)"
                        )
                    elif resp.status_code in (401, 403):
                        detail = f"HTTP {resp.status_code} — Apify token rejected"
                    else:
                        detail = f"HTTP {resp.status_code}: {body[:120]}"
                    self._record("Apify (Facebook Ad Library)", "error", detail)
                    return []
        except Exception as e:
            logger.error(f"Apify scraper request failed: {e}")
            self._record("Apify (Facebook Ad Library)", "error", f"request failed: {e}")

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
