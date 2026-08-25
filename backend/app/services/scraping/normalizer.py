from typing import Dict, Any, Optional
from app.models.creative import Creative as DBCreative, generate_uuid
from app.models.creative_score import CreativeScore as DBCreativeScore
from app.services.scraping.base import RawCreative

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

    # Data Honesty Rule: If not from the official Meta API, these are arbitrary guesses
    # and should be dropped unless explicitly permitted.
    impressions_est = raw.impressions_est
    spend_band = raw.spend_band
    engagement_rate = None  # Only available from official APIs with verified data
    ctr_est = None  # Only available from official APIs with verified data

    data_source = getattr(raw, "data_source", "meta_official")
    is_estimated = getattr(raw, "is_estimated", True)

    if data_source != "meta_official":
        impressions_est = None
        spend_band = None
        engagement_rate = None
        ctr_est = None
        is_estimated = True

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
        impressions_est=impressions_est,
        is_estimated=is_estimated,
        data_source=data_source,
        spend_band=spend_band,
        engagement_rate=engagement_rate,
        ctr_est=ctr_est
    )
    
    # AI scores are set to None until a real LLM scoring pass is run.
    # Do not generate random scores — they are displayed as real scores to users.
    score = DBCreativeScore(
        creative_id=c_id,
        hook=None,
        clarity=None,
        retention=None,
        composite=None
    )
    
    return creative, score
