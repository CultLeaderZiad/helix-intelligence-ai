"""
Helix Scout Atlas Pipeline
Deterministic classification & scoring + LLM outreach generation.
Zero Apify. Zero Relevance AI runtime dependency. Owned inside Helix Intelligence.
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from app.services.ai.ai_router import MultiTierAIProvider

logger = logging.getLogger(__name__)


# --- Deterministic Influence & Engagement Classifiers ---

def influence_level(followers: Optional[int]) -> str:
    """Classifies follower count into influence tier."""
    if followers is None or followers < 1000:
        return "unknown"
    if followers < 10_000:
        return "nano"
    if followers < 50_000:
        return "micro"
    if followers < 500_000:
        return "mid"
    return "macro"


def engagement_quality(rate: Optional[float]) -> str:
    """Classifies engagement rate."""
    if rate is None:
        return "unknown"
    if rate >= 0.05:
        return "high"
    if rate >= 0.02:
        return "medium"
    return "low"


def relevance_score(
    category_match_0_1: float,
    eng_quality: str,
    influence: str,
    weights: tuple = (0.4, 0.3, 0.3)
) -> int:
    """
    Weighted Atlas relevance score (0..100).
    Formula: Category Match (40%) + Engagement/Contact Verifiability (30%) + Influence Tier (30%).
    Note: macro is scored 0.7 (slightly lower than mid at 0.9) due to lower B2B buying/decision-maker accessibility.
    """
    eng_map = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.4}
    inf_map = {"nano": 0.5, "micro": 0.75, "mid": 0.9, "macro": 0.7, "unknown": 0.4}

    e_val = eng_map.get(eng_quality.lower(), 0.4)
    i_val = inf_map.get(influence.lower(), 0.4)
    c_val = min(1.0, max(0.0, category_match_0_1))

    s = 100 * (weights[0] * c_val + weights[1] * e_val + weights[2] * i_val)
    return int(min(100, max(0, round(s))))


# --- Account Type Classifier ---

def classify_account_type(bio: str, name: str, captions: List[str]) -> str:
    """Classifies profile into business | influencer | personal | unknown."""
    corpus = f"{bio} {name} {' '.join(captions)}".lower()

    business_keywords = [
        "clinic", "hospital", "doctor", "dr.", "medical", "dental", "surgery",
        "aesthetic", "salon", "spa", "ltd", "inc", "co.", "agency", "studio",
        "services", "store", "shop", "brand", "official", "booking", "appointments",
        "dm for orders", "headquarters", "center", "firm", "solutions", "boutique",
        "founder", "ceo", "co-founder", "director", "managing partner", "team", "b2b"
    ]
    influencer_keywords = [
        "creator", "influencer", "model", "blogger", "public figure", "athlete",
        "artist", "content creator", "actor", "musician", "lifestyle", "vlogger",
        "ambassador", "collabs", "pr:", "mgmt:", "collaborations"
    ]

    if any(k in corpus for k in business_keywords):
        return "business"
    if any(k in corpus for k in influencer_keywords):
        return "influencer"
    if len(bio.strip()) > 0:
        return "personal"
    return "unknown"


# --- Topic & Niche Extraction ---

def extract_niches(bio: str, captions: List[str], target_category: Optional[str]) -> tuple[str, List[str]]:
    corpus = f"{bio} {' '.join(captions)}".lower()
    known_niches = {
        "beauty": ["beauty", "skin", "skincare", "cosmetic", "glow", "makeup", "hair", "laser"],
        "aesthetics & healthcare": ["clinic", "dental", "dentist", "medical", "wellness", "aesthetic", "dermatology"],
        "fitness & wellness": ["fitness", "gym", "coach", "workout", "nutrition", "training"],
        "hospitality & food": ["coffee", "roastery", "cafe", "restaurant", "food", "dining", "bakery"],
        "fashion & luxury": ["fashion", "luxury", "style", "apparel", "wear", "jewelry"],
        "b2b & tech": ["software", "ai", "tech", "agency", "marketing", "consulting", "enterprise", "saas"],
        "ecommerce & retail": ["shop", "store", "collection", "orders", "shipping"],
    }

    matched = []
    for niche_label, kws in known_niches.items():
        if any(k in corpus for k in kws):
            matched.append(niche_label)

    if target_category and target_category.strip():
        primary = target_category.strip()
        secondary = [m for m in matched if m.lower() != primary.lower()]
        return primary, secondary

    primary = matched[0] if matched else "General Business"
    secondary = matched[1:] if len(matched) > 1 else []
    return primary, secondary


# --- Category Match Calculation ---

def calculate_category_match(corpus: str, target_category: Optional[str]) -> tuple[float, str]:
    if not target_category or not target_category.strip():
        return 0.6, "General target match"

    tokens = [t.lower().strip() for t in re.split(r"[\s,/]+", target_category) if len(t) > 2]
    if not tokens:
        return 0.5, "Standard category match"

    matches = [t for t in tokens if t in corpus]
    ratio = len(matches) / len(tokens)
    # Normal scale: 0 matches -> 0.25, full match -> 1.0
    val = min(1.0, max(0.2, 0.2 + (ratio * 0.8)))
    desc = f"Matched {len(matches)}/{len(tokens)} context keywords: {', '.join(matches)}" if matches else "Partial niche overlap"
    return val, desc


# --- LLM Outreach Generation ---

async def generate_atlas_outreach(
    lead_name: str,
    handle: str,
    platform: str,
    bio: str,
    website: Optional[str],
    target_category: Optional[str],
    captions: List[str],
    primary_niche: str,
    account_type: str,
) -> Dict[str, Any]:
    """Generates personalized outreach draft via Helix AI Router."""
    provider = MultiTierAIProvider()

    prompt = f"""You are the Helix Atlas Outreach Engine. Generate personalized, high-converting outreach for this verified lead:
- Platform: {platform}
- Handle: @{handle}
- Name: {lead_name}
- Account Type: {account_type}
- Primary Niche: {primary_niche}
- Target Context: {target_category or primary_niche}
- Bio: {bio}
- Website: {website or 'N/A'}
- Recent Content/Captions: {' | '.join(captions[:3]) if captions else 'N/A'}

Rules:
1. Subject line must be punchy, curiosity-inducing, and under 9 words.
2. Email body must be concise (80-120 words), direct, professional, referencing 1 specific detail from their bio/content.
3. DM draft must be friendly, conversational (2-3 sentences max) for Instagram/LinkedIn.
4. Provide 2-3 specific personalization points.

Output MUST be valid JSON only with this exact structure:
{{
  "email_subject": "...",
  "email_body": "...",
  "dm_body": "...",
  "personalization_points": ["point 1", "point 2"]
}}"""

    messages = [
        {"role": "system", "content": "You are a professional B2B cold outreach specialist. Respond with strictly valid JSON only. No markdown fences."},
        {"role": "user", "content": prompt}
    ]

    try:
        raw_res = await provider._call_api(messages)
        clean_res = raw_res.strip()
        if clean_res.startswith("```"):
            clean_res = re.sub(r"^```[a-zA-Z]*\n?", "", clean_res)
            clean_res = re.sub(r"\n?```$", "", clean_res).strip()
        data = json.loads(clean_res)
        return {
            "email_subject": data.get("email_subject") or f"Quick question regarding {lead_name}",
            "email_body": data.get("email_body") or "",
            "dm_body": data.get("dm_body") or "",
            "personalization_points": data.get("personalization_points") or [f"Referenced {primary_niche} focus"]
        }
    except Exception as e:
        logger.warning(f"LLM outreach generation fallback: {e}")
        return {
            "email_subject": f"Partnership opportunity · {lead_name}",
            "email_body": f"Hi {lead_name},\n\nI came across your profile (@{handle}) and was impressed by your work in {primary_niche}. We are currently working with top partners in {target_category or primary_niche} to streamline client acquisition and operational AI.\n\nWould you be open to a brief 5-minute chat this week?\n\nBest regards,\nHelix Intelligence Team",
            "dm_body": f"Hey {lead_name}! Love what you're doing in {primary_niche}. Sent you a quick note regarding an initiative we're running for {target_category or 'leaders in your space'}.",
            "personalization_points": [f"Referenced @{handle} niche in {primary_niche}"]
        }


# --- Main Pipeline Runner ---

async def run_atlas_pipeline(
    raw_lead: Dict[str, Any],
    target_category: Optional[str] = None,
    generate_outreach: bool = True,
) -> Dict[str, Any]:
    """
    Executes the full Atlas analyze -> score -> outreach pipeline.
    Returns complete Atlas JSON contract.
    """
    platform = raw_lead.get("platform", "instagram")
    handle = raw_lead.get("handle", "")
    name = raw_lead.get("name") or raw_lead.get("full_name") or handle
    bio = raw_lead.get("bio") or ""
    website = raw_lead.get("website")
    followers = raw_lead.get("followers") or raw_lead.get("follower_count")
    is_verified = bool(raw_lead.get("is_verified"))
    email = raw_lead.get("email")
    email_source = raw_lead.get("email_source")
    phone = raw_lead.get("phone")
    captions = raw_lead.get("captions") or []
    # If recent_posts is provided as list of dicts, extract captions
    if "recent_posts" in raw_lead and isinstance(raw_lead["recent_posts"], list):
        for p in raw_lead["recent_posts"]:
            if isinstance(p, dict) and p.get("caption"):
                captions.append(p["caption"])
    avg_eng_rate = raw_lead.get("avg_engagement_rate")
    scrape_status = raw_lead.get("scrape_status", "ok")
    error = raw_lead.get("error")

    # 1. Profile Analysis
    account_type = classify_account_type(bio, name, captions)
    primary_niche, secondary_niches = extract_niches(bio, captions, target_category)
    inf_tier = influence_level(followers)
    eng_qual = engagement_quality(avg_eng_rate) if avg_eng_rate is not None else ("high" if (email and website) else "medium" if email else "unknown")

    # 2. Lead Scoring
    corpus = f"{bio} {' '.join(captions)}".lower()
    cat_match_0_1, category_match_desc = calculate_category_match(corpus, target_category)
    score = relevance_score(cat_match_0_1, eng_qual, inf_tier)

    # Priority determination
    if score >= 75:
        priority = "high"
    elif score >= 50:
        priority = "medium"
    else:
        priority = "low"

    reasoning = (
        f"Score {score}/100 [Category: {int(cat_match_0_1*40)}/40, "
        f"Engagement/Contact: {eng_qual}, Influence: {inf_tier}]. "
        f"Priority: {priority.upper()}."
    )

    # 3. Outreach Generation (Medium and High priority only)
    outreach_data = {
        "email_subject": "",
        "email_body": "",
        "dm_body": "",
        "personalization_points": [],
    }

    if generate_outreach and priority in ("medium", "high") and scrape_status != "not_found":
        outreach_data = await generate_atlas_outreach(
            lead_name=name,
            handle=handle,
            platform=platform,
            bio=bio,
            website=website,
            target_category=target_category,
            captions=captions,
            primary_niche=primary_niche,
            account_type=account_type,
        )

    # 4. Final Atlas Contract Assembly
    atlas_result = {
        "profile_analysis": {
            "account_type": account_type,
            "primary_niche": primary_niche,
            "secondary_niches": secondary_niches,
            "influence_level": inf_tier,
            "engagement_metrics": {
                "follower_count": followers or 0,
                "avg_engagement_rate": avg_eng_rate,
                "engagement_quality": eng_qual,
            },
        },
        "lead_scoring": {
            "relevance_score": score,
            "priority_level": priority,
            "category_match": category_match_desc,
            "reasoning": reasoning,
        },
        "enrichment_data": {
            "email": email,
            "email_source": email_source,
            "phone": phone,
            "website": website,
            "key_topics": [primary_niche] + secondary_niches[:3],
            "content_sentiment": "neutral",
        },
        "outreach": outreach_data,
        "meta": {
            "platform": platform,
            "handle": handle,
            "profile_url": raw_lead.get("profile_url") or f"https://{platform}.com/{handle}",
            "scrape_status": scrape_status,
            "error": error,
        },
    }

    return atlas_result
