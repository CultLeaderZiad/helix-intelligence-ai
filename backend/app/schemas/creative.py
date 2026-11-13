from pydantic import BaseModel
from typing import Optional, List

class Scores(BaseModel):
    hook: Optional[float] = None
    clarity: Optional[float] = None
    retention: Optional[float] = None
    composite: Optional[float] = None
    # Heuristic rubric metadata. Observed platform performance is not this object.
    basis: Optional[str] = None
    scale: Optional[str] = None
    version: Optional[str] = None

class CreativeMetrics(BaseModel):
    impressions_est: Optional[int] = None
    is_impression_estimate: Optional[bool] = True
    spend_band: Optional[str] = None
    engagement_rate: Optional[float] = None
    ctr_est: Optional[float] = None

class CopyVariant(BaseModel):
    body: str = ""
    title: str = ""
    description: str = ""

class SavedAdNote(BaseModel):
    id: str
    body: str
    author_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Creative(BaseModel):
    id: str
    brand_id: str
    brand_name: Optional[str] = None
    platform: str
    format: str
    source_type: Optional[str] = "ad" # 'ad' | 'organic_content_proxy'
    headline: str
    body: str
    cta: Optional[str] = None
    landing_domain: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_ratio: Optional[str] = None
    duration_seconds: Optional[int] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    days_active: Optional[int] = None
    source_ad_id: Optional[str] = None
    permalink: Optional[str] = None
    fetched_at: Optional[str] = None
    variant_count: int
    # Every copy variant the provider returned for this ad (dynamic creative).
    copy_variants: List[CopyVariant] = []
    # Ads in one search sharing the same copy share a concept id; variant_count
    # is then the number of ads in that concept.
    concept_id: Optional[str] = None
    # Advertiser page id when the provider returned one (W9-2 "Monitor this brand").
    page_id: Optional[str] = None
    # Saved-ads list only (W9-2): the caller's tags and notes on this ad.
    tags: List[str] = []
    notes: List[SavedAdNote] = []
    scores: Scores
    metrics: CreativeMetrics
    pattern_ids: List[str]

class Brand(BaseModel):
    id: str
    name: str
    domain: str
    category: str
    ad_count: int
    first_seen: str



from app.schemas.common import Paginated  # noqa: E402


class CreativeResults(Paginated[Creative]):
    """Discover results. When a longevity filter is active, ads whose run
    length is unknown cannot be shown as "running N+ days"; their count is
    reported instead of silently treating them as 0."""
    hidden_unknown_run_length: Optional[int] = None


class StoredResults(CreativeResults):
    """``/discovery/stored-results``: which stored search answered, and when."""
    job_id: str
    searched_at: Optional[str] = None
    records_used: int = 0
