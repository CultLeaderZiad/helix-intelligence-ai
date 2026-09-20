"""
Scout & Atlas Pydantic schemas
Matches Atlas Data Contract for Helix Intelligence
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EngagementMetrics(BaseModel):
    follower_count: int = 0
    avg_engagement_rate: Optional[float] = None
    engagement_quality: str = Field(default="unknown", description="high|medium|low|unknown")


class ProfileAnalysis(BaseModel):
    account_type: str = Field(default="unknown", description="business|influencer|personal|unknown")
    primary_niche: str = ""
    secondary_niches: List[str] = Field(default_factory=list)
    influence_level: str = Field(default="unknown", description="nano|micro|mid|macro|unknown")
    engagement_metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)


class LeadScoring(BaseModel):
    relevance_score: int = Field(default=0, ge=0, le=100)
    priority_level: str = Field(default="low", description="high|medium|low")
    category_match: str = ""
    reasoning: str = ""


class EnrichmentData(BaseModel):
    email: Optional[str] = None
    email_source: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    content_sentiment: str = "neutral"


class OutreachDraft(BaseModel):
    email_subject: str = ""
    email_body: str = ""
    dm_body: str = ""
    personalization_points: List[str] = Field(default_factory=list)


class AtlasMeta(BaseModel):
    platform: str = "instagram"
    handle: str = ""
    profile_url: str = ""
    scrape_status: str = Field(default="ok", description="ok|needs_manual_review|error")
    error: Optional[str] = None


class AtlasLeadContract(BaseModel):
    """The canonical Atlas Data Contract."""
    profile_analysis: ProfileAnalysis = Field(default_factory=ProfileAnalysis)
    lead_scoring: LeadScoring = Field(default_factory=LeadScoring)
    enrichment_data: EnrichmentData = Field(default_factory=EnrichmentData)
    outreach: OutreachDraft = Field(default_factory=OutreachDraft)
    meta: AtlasMeta = Field(default_factory=AtlasMeta)


class CreateScoutJobRequest(BaseModel):
    mode: str = Field(default="social_atlas", description="social_atlas|social|maps")
    platforms: List[str] = Field(default=["instagram"], description="Target platforms")
    handles: List[str] = Field(default_factory=list, description="Handles or URLs")
    enrich_emails: bool = Field(default=True, description="Enrich websites for direct contact")
    target_category: str = Field(default="General B2B", min_length=2, description="Target category or business context")
    generate_outreach: bool = Field(default=True, description="Generate cold email and DM drafts if score >= 50")


class ScoutLeadOut(BaseModel):
    id: str
    job_id: str
    platform: str
    handle: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_url: Optional[str] = None
    lead_score: int = 0
    scrape_status: str = "ok"
    account_type: Optional[str] = None
    priority_level: Optional[str] = None
    atlas: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class ScoutJobOut(BaseModel):
    id: str
    org_id: str
    status: str
    total_handles: int
    processed_count: int
    leads_count: int
    cost_credits: float
    target_category: Optional[str] = None
    generate_outreach: bool = True
    logs: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    finished_at: Optional[str] = None
