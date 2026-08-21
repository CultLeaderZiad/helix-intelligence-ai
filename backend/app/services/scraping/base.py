from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

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
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    days_active: int = 1
    variant_count: int = 1

    # Optional fields for raw metrics if provided by the ad library directly
    impressions_est: Optional[int] = None
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
