from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic import BaseModel


class ProviderFailure(Exception):
    """A provider call failed. An empty list is not a stand-in for this."""

    def __init__(self, provider: str, message: str, http_status: Optional[int] = None):
        self.provider = provider
        self.http_status = http_status
        super().__init__(message)


class RawCreative(BaseModel):
    """
    Standardized schema for a creative scraped from any ad library before normalization.
    """
    platform: str
    format: str = "video"
    brand_name: str
    headline: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    landing_domain: Optional[str] = None
    landing_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_ratio: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    days_active: int = 1
    # False when the provider did not supply a start date. The normalizer then stores null.
    days_known: bool = True
    variant_count: int = 1
    source_ad_id: Optional[str] = None
    permalink: Optional[str] = None
    fetched_at: Optional[str] = None
    provider: Optional[str] = None
    raw: Optional[dict[str, Any]] = None

    # Optional fields for raw metrics if provided by the ad library directly
    impressions_est: Optional[int] = None
    is_estimated: bool = True
    data_source: str = "meta_official" # 'meta_official' | 'ad_library_scrape' | 'organic_content_proxy'
    spend_band: Optional[str] = None

class ScraperProvider(ABC):
    """
    Abstract interface for scraping ad libraries for creatives.
    """

    @abstractmethod
    async def search(self, query: str) -> List[RawCreative]:
        """
        Search the ad library with a given query (e.g. brand name or keyword).
        Returns a list of RawCreative objects.
        """
        pass
