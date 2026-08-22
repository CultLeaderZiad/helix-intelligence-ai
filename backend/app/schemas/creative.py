from pydantic import BaseModel
from typing import Optional, List

class Scores(BaseModel):
    hook: Optional[float] = None
    clarity: Optional[float] = None
    retention: Optional[float] = None
    composite: Optional[float] = None

class CreativeMetrics(BaseModel):
    impressions_est: Optional[int] = None
    is_impression_estimate: Optional[bool] = True
    spend_band: Optional[str] = None
    engagement_rate: Optional[float] = None
    ctr_est: Optional[float] = None

class Creative(BaseModel):
    id: str
    brand_id: str
    platform: str
    format: str
    source_type: Optional[str] = "ad" # 'ad' | 'organic_content_proxy'
    headline: str
    body: str
    cta: str
    landing_domain: Optional[str] = None
    thumbnail_ratio: Optional[str] = None
    duration_seconds: Optional[int] = None
    first_seen: str
    last_seen: str
    days_active: int
    variant_count: int
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

