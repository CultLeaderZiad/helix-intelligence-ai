"""Pydantic schemas for Scout Lead Generation (scrapling_engine)."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LeadGenBrief(BaseModel):
    icp: str = Field(..., min_length=3, description="Ideal customer profile, required")
    geos: List[str] = Field(default_factory=lambda: ["SA", "AE", "JO", "EG"])
    languages: List[str] = Field(default_factory=lambda: ["ar", "en"])
    exclude_domains: List[str] = Field(default_factory=list)
    max_pages: int = Field(default=100, ge=1)
    max_leads: int = Field(default=50, ge=1)
    credit_budget: float = Field(default=50.0, ge=0)
    outreach_min_score: int = Field(default=50, ge=0, le=100)


class LeadGenSeeds(BaseModel):
    urls: List[str] = Field(default_factory=list)
    sitemap_url: Optional[str] = None
    shopify_url: Optional[str] = None
    domains_csv: Optional[str] = None   # raw CSV/JSONL content (newline-separated domains or URLs)


class CreateLeadGenJobRequest(BaseModel):
    brief: LeadGenBrief
    seeds: LeadGenSeeds
    engine_default: str = Field(default="stealth")   # http | stealth | dynamic
    mode: str = Field(default="crawl")               # crawl | sitemap | shopify | csv_feed | digest
    recipe_id: Optional[str] = None
    robots_obey: bool = True
    adaptive: bool = True
    capture_xhr_pattern: Optional[str] = None
    enrich_emails: bool = True
    generate_outreach: bool = True
    proxy_mode: str = Field(default="off")           # off | org | job


class LeadGenJobEnvelope(BaseModel):
    """Honest job envelope — never fabricates progress or leads."""
    job_id: str
    status: str
    stage: str
    stage_label: str
    stage_index: int
    stages_total: int
    logs: List[str] = Field(default_factory=list)
    leads_count: int = 0
    pages_fetched: int = 0
    pages_blocked: int = 0
    elapsed_ms: int = 0
    credits_used: float = 0.0
    robots_obey: bool = True
    engine_default: str = "stealth"
    mode: str = "crawl"
    recipe_id: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: Optional[str] = None


class LeadGenLeadOut(BaseModel):
    id: str
    job_id: str
    company_name: Optional[str] = None
    website: Optional[str] = None
    domain: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    socials: Dict[str, Any] = Field(default_factory=dict)
    address: Optional[str] = None
    decision_makers: List[Any] = Field(default_factory=list)
    markdown_excerpt: Optional[str] = None
    markdown_artifact_path: Optional[str] = None
    extract_status: str = "empty"
    fetch_status: str = "ok"
    engine_used: str = "stealth"
    email_source: str = "none"
    phone_source: str = "none"
    lead_score: int = 0
    priority: Optional[str] = None
    outreach: Optional[Dict[str, Any]] = None
    sources: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
