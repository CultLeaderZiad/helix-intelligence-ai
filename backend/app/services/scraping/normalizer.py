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
HEURISTIC_VERSION = "copy-heuristics-v2"
HEURISTIC_SCALE = "0-10"


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

    brand_name = (raw.brand_name or brand_label or "Unknown").strip()
    media_url = getattr(raw, "media_url", None)
    thumbnail_url = getattr(raw, "thumbnail_url", None)

    creative = DBCreative(
        id=c_id,
        job_id=job_id,
        brand_id=brand_id,
        brand_name=brand_name,
        platform=raw.platform,
        format=raw.format,
        headline=headline,
        body=body,
        cta=cta,
        landing_domain=raw.landing_domain,
        media_url=media_url,
        thumbnail_url=thumbnail_url,
        thumbnail_ratio=raw.thumbnail_ratio,
        duration_seconds=raw.duration_seconds,
        first_seen=raw.first_seen,
        last_seen=raw.last_seen,
        days_active=raw.days_active if getattr(raw, "_days_known", True) else None,
        variant_count=raw.variant_count,
        impressions_est=impressions_est,
        is_estimated=is_estimated if impressions_est is not None else None,
        data_source=data_source,
        spend_band=spend_band,
        engagement_rate=engagement_rate,
        ctr_est=ctr_est,
        source_ad_id=getattr(raw, "_source_ad_id", None),
        permalink=getattr(raw, "_permalink", None),
        fetched_at=None,
        provenance_json=getattr(raw, "_provenance", None),
        score_basis="heuristic",
        score_scale=HEURISTIC_SCALE,
        heuristic_version=HEURISTIC_VERSION,
    )
    fetched = getattr(raw, "_fetched_at", None)
    if fetched:
        from datetime import datetime
        try:
            creative.fetched_at = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
        except Exception:
            creative.fetched_at = None

    # Rubric only. Points are added for text features that are present.
    # A zero means the rubric saw no signal, not a measured performance score.
    hl_lower = (headline or "").lower()
    hook_score = 0.0
    if any(trigger in hl_lower for trigger in ["how", "why", "secret", "never", "stop", "unlock", "discover", "reveal", "?"]):
        hook_score += 4.0
    if any(char.isdigit() for char in (headline or "")):
        hook_score += 2.0
    if headline and 10 < len(headline) < 80:
        hook_score += 2.0
    hook_score = min(10.0, round(hook_score, 1))

    clarity_score = 0.0
    if cta and cta.lower() not in ("none", ""):
        clarity_score += 4.0
    if len(body or "") > 40:
        clarity_score += 3.0
    if body and ("\n" in body or "•" in body or "-" in body):
        clarity_score += 2.0
    clarity_score = min(10.0, round(clarity_score, 1))

    retention_score = 0.0
    if raw.format == "video":
        retention_score += 4.0
    if getattr(raw, "_days_known", False) and (raw.days_active or 0) > 7:
        retention_score += 3.0
    retention_score = min(10.0, round(retention_score, 1))

    composite_score = round(0.4 * hook_score + 0.3 * clarity_score + 0.3 * retention_score, 1)

    score = DBCreativeScore(
        creative_id=c_id,
        hook=hook_score,
        clarity=clarity_score,
        retention=retention_score,
        composite=composite_score
    )
    
    return creative, score
