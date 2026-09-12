import logging
from typing import List, Optional
from app.services.scraping.base import ScraperProvider, RawCreative
from app.services.scraping.metapi_provider import MetapiProvider

logger = logging.getLogger(__name__)

# ==============================================================================
# CANONICAL AD DISCOVERY PROVIDER CHAIN (Single Source of Truth)
# Metapi only. Adyntel, the official Meta Graph API, and Apify were removed:
# Adyntel/Apify added no coverage Metapi doesn't already provide, and the
# free Meta Graph ads_archive endpoint only archives political/social-issue
# ads worldwide or ads delivered to EU/UK audiences — it cannot answer a
# generic commercial keyword search, so it never usefully fires as a
# fallback for this product.
# ==============================================================================
DISCOVERY_PROVIDER_CHAIN = [
    "metapi",
]


class AdLibraryProvider(ScraperProvider):
    """
    Ad Discovery Provider and Single Source of Truth for ad search.
    Delegates directly to Metapi — the only configured provider.
    """

    def __init__(self, db=None, org_id: Optional[str] = None, user_id: Optional[str] = None):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id

        self.metapi_provider = MetapiProvider(db, str(org_id) if org_id else "", str(user_id) if user_id else "")

        # Execution tracking
        self.last_provider_used: str = "none"
        self.sources_tried: List[str] = []

    async def search(
        self,
        query: str,
        max_records: int = 15,
        filters: Optional[dict] = None,
        progress_callback=None
    ) -> List[RawCreative]:
        """Executes the search against Metapi (the only configured provider)."""
        assert max_records and max_records > 0, "Safety Violation: max_records missing or invalid"
        if not query or not query.strip():
            return []

        cleaned_query = query.strip()
        self.sources_tried = []
        self.last_provider_used = "none"

        if not self.metapi_provider.metapi_api_key:
            logger.warning("[AdDiscovery] Metapi is not configured (METAPI_API_KEY missing). No search performed.")
            return []

        self.sources_tried.append("Metapi")
        logger.info(f"[AdDiscovery] Searching via Metapi for query='{cleaned_query}'")
        try:
            creatives = await self.metapi_provider.search(
                cleaned_query,
                max_records=max_records,
                filters=filters,
                progress_callback=progress_callback
            )
            if creatives:
                self.last_provider_used = "metapi"
                logger.info(f"[AdDiscovery] Metapi succeeded with {len(creatives)} creatives")
                return creatives
            logger.info("[AdDiscovery] Metapi returned 0 creatives")
        except Exception as e:
            logger.warning(f"[AdDiscovery] Metapi search failed: {e}")

        logger.info(f"[AdDiscovery] No results for query='{cleaned_query}'.")
        return []
