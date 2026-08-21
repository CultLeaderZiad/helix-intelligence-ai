from typing import Dict, Any, Optional
from app.models.creative import Creative as DBCreative, generate_uuid
from app.models.creative_score import CreativeScore as DBCreativeScore
from app.services.scraping.base import RawCreative
import random

def normalize_creative(
    raw: RawCreative,
    job_id: str,
    brand_id: str,
    enriched_data: Optional[Dict[str, Any]] = None
) -> tuple[DBCreative, DBCreativeScore]:
    """
    Normalizes a RawCreative and optional ScrapeGraph enrichment data into
    our database models.
    """
    c_id = generate_uuid()
    
    # Base mapping from raw
    headline = raw.headline
    cta = raw.cta
    body = raw.body
    
    # Enrichment mapping if ScrapeGraph succeeded
    if enriched_data:
        # We can append or override based on strategy. We'll prioritize the 
        # actual ad text if it exists, otherwise use landing page data.
        if not headline and enriched_data.get("headline"):
            headline = enriched_data.get("headline")
            
        if not cta and enriched_data.get("cta"):
            cta = enriched_data.get("cta")
            
        # We can append positioning or offer to body if body was empty
        if not body:
            parts = []
            if enriched_data.get("offer"):
                parts.append(enriched_data.get("offer"))
            if enriched_data.get("positioning"):
                parts.append(enriched_data.get("positioning"))
            if parts:
                body = " | ".join(parts)

    creative = DBCreative(
        id=c_id,
        job_id=job_id,
        brand_id=brand_id,
        platform=raw.platform,
        format=raw.format,
        headline=headline,
        body=body,
        cta=cta,
        landing_domain=raw.landing_domain,
        thumbnail_ratio=raw.thumbnail_ratio,
        duration_seconds=raw.duration_seconds,
        first_seen=raw.first_seen,
        last_seen=raw.last_seen,
        days_active=raw.days_active,
        variant_count=raw.variant_count,
        impressions_est=raw.impressions_est,
        spend_band=raw.spend_band,
        # Mocking engagement for MVP purposes unless provided by raw source
        engagement_rate=random.uniform(0.01, 0.08),
        ctr_est=random.uniform(0.005, 0.03)
    )
    
    # For MVP, we will mock the AI scores (hook, clarity, retention) 
    # based on heuristics or randomly if we don't run an LLM scoring pass per creative.
    hook = random.uniform(60, 95)
    clarity = random.uniform(70, 98)
    retention = random.uniform(50, 90)
    composite = (hook + clarity + retention) / 3.0
    
    score = DBCreativeScore(
        creative_id=c_id,
        hook=hook,
        clarity=clarity,
        retention=retention,
        composite=composite
    )
    
    return creative, score
