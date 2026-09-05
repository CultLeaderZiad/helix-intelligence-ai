from typing import Dict, Any, Optional, Tuple
import re
from app.models.creative import Creative as DBCreative, generate_uuid
from app.models.creative_score import CreativeScore as DBCreativeScore
from app.services.scraping.base import RawCreative

# Meta Ad Library dynamic-creative macros ({{product.brand}}, {{page.name}},
# ...) arrive unrendered in provider snapshots. They are not ad copy — a
# record whose text is only macros is template noise, not a real creative.
_MACRO_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

_BRAND_MACROS = {"product.brand", "brand", "page.name", "page_name", "brand.name"}


def clean_template_macros(text: Optional[str], brand_label: str = "") -> str:
    """Resolve brand macros to the real brand name, strip the rest."""
    if not text:
        return ""

    def _sub(match: "re.Match") -> str:
        token = match.group(1).lower()
        if token in _BRAND_MACROS and brand_label:
            return brand_label
        return ""

    return _MACRO_RE.sub(_sub, text).strip()


def normalize_creative(
    raw: RawCreative,
    job_id: str,
    brand_id: str,
    enriched_data: Optional[Dict[str, Any]] = None,
    brand_label: str = "",
) -> Optional[Tuple[DBCreative, DBCreativeScore]]:
    """
    Normalizes a RawCreative and optional ScrapeGraph enrichment data into
    our database models. Returns None when the record carries no real ad
    copy (pure template macros) — callers must skip such records rather
    than store them as genuine creatives.
    """
    c_id = generate_uuid()

    # Base mapping from raw, with unrendered dynamic-creative macros
    # resolved (brand macros -> the searched brand) or stripped.
    headline = clean_template_macros(raw.headline, brand_label)
    cta = clean_template_macros(raw.cta, brand_label)
    body = clean_template_macros(raw.body, brand_label)
    
    # Enrichment mapping if ScrapeGraph succeeded
    if enriched_data:
        # We can append or override based on strategy. We'll prioritize the
        # actual ad text if it exists, otherwise use landing page data.
        if not headline and enriched_data.get("headline"):
            headline = clean_template_macros(enriched_data.get("headline"), brand_label)

        if not cta and enriched_data.get("cta"):
            cta = clean_template_macros(enriched_data.get("cta"), brand_label)

        # We can append positioning or offer to body if body was empty
        if not body:
            parts = []
            if enriched_data.get("offer"):
                parts.append(enriched_data.get("offer"))
            if enriched_data.get("positioning"):
                parts.append(enriched_data.get("positioning"))
            if parts:
                body = clean_template_macros(" | ".join(parts), brand_label)

    # A record with no headline AND no body after macro cleaning is template
    # noise, not a creative — reject it instead of storing an empty shell.
    if not headline and not body:
        return None

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
