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

# Influence Bands
def get_influence_level(followers: Optional[int]) -> str:
    if followers is None or followers <= 0:
        return "unknown"
    if followers < 10000:
        return "nano"
    if followers < 50000:
        return "micro"
    if followers < 500000:
        return "mid"
    return "macro"

# Account Type Classification
def classify_account_type(bio: str, name: str, captions: List[str]) -> str:
    corpus = f"{bio} {name} {' '.join(captions)}".lower()
    
    business_keywords = [
        "clinic", "hospital", "doctor", "dr.", "medical", "dental", "surgery",
        "aesthetic", "salon", "spa", "ltd", "inc", "co.", "agency", "studio",
        "services", "store", "shop", "brand", "official", "booking", "appointments",
        "dm for orders", "headquarters", "center", "firm", "solutions", "boutique"
    ]
    influencer_keywords = [
        "creator", "influencer", "model", "blogger", "public figure", "athlete",
        "artist", "content creator", "actor", "musician", "lifestyle", "vlogger",
        "ambassador", "collabs", "pr:", "mgmt:"
    ]
    
    if any(k in corpus for k in business_keywords):
        return "business"
    if any(k in corpus for k in influencer_keywords):
        return "influencer"
    if len(bio.strip()) > 0:
        return "personal"
    return "unknown"

# Topic & Niche Extraction
def extract_niches(bio: str, captions: List[str], target_category: Optional[str]) -> tuple[str, List[str]]:
    corpus = f"{bio} {' '.join(captions)}".lower()
    known_niches = {
        "beauty": ["beauty", "skin", "skincare", "cosmetic", "glow", "makeup", "hair", "laser"],
        "aesthetics & healthcare": ["clinic", "dental", "dentist", "medical", "wellness", "aesthetic", "dermatology"],
        "fitness & wellness": ["fitness", "gym", "coach", "workout", "nutrition", "training"],
        "hospitality & food": ["coffee", "roastery", "cafe", "restaurant", "food", "dining", "bakery"],
        "fashion & luxury": ["fashion", "luxury", "style", "apparel", "wear", "jewelry"],
        "b2b & tech": ["software", "ai", "tech", "agency", "marketing", "consulting", "enterprise"],
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

# Deterministic Scoring
# Formula: Category Match (40%) + Engagement/Contact Verifiability (30%) + Influence Band (30%)
def compute_atlas_score(
    bio: str,
    captions: List[str],
    target_category: Optional[str],
    has_email: bool,
    has_phone: bool,
    has_website: bool,
    is_verified: bool,
    influence_level: str,
) -> tuple[int, str, str, str]:
    corpus = f"{bio} {' '.join(captions)}".lower()
    
    # 1. Category Match (0 to 40 pts)
    category_match_score = 15  # baseline
    cat_match_label = "General match"
    if target_category and target_category.strip():
        words = [w.lower().strip() for w in re.split(r"[\s,/]+", target_category) if len(w) > 2]
        matches = [w for w in words if w in corpus]
        if len(words) > 0:
            ratio = len(matches) / len(words)
            category_match_score = int(10 + (ratio * 30))
            category_match_score = min(40, max(10, category_match_score))
            cat_match_label = f"Matched {len(matches)}/{len(words)} keywords: {', '.join(matches)}" if matches else "Partial niche overlap"
    else:
        category_match_score = 25
        cat_match_label = "Standard target category"

    # 2. Engagement & Contact Verifiability (0 to 30 pts)
    engagement_score = 5
    if has_email:
        engagement_score += 12
    if has_phone:
        engagement_score += 5
    if has_website:
        engagement_score += 5
    if is_verified:
        engagement_score += 3
    engagement_score = min(30, engagement_score)

    # 3. Influence Band (0 to 30 pts)
    # Micro/Mid have the highest conversion in B2B & creator partnerships
    influence_scores = {
        "micro": 30,
        "mid": 25,
        "nano": 20,
        "macro": 15,
        "unknown": 10,
    }
    influence_score = influence_scores.get(influence_level, 10)

    total_score = min(100, max(0, category_match_score + engagement_score + influence_score))

    # Priority Level
    if total_score >= 70:
        priority = "high"
    elif total_score >= 50:
        priority = "medium"
    else:
        priority = "low"

    reasoning = (
        f"Score {total_score}/100 [Category: {category_match_score}/40, "
        f"Contact/Engagement: {engagement_score}/30, Influence: {influence_score}/30]. "
        f"Priority: {priority.upper()}."
    )

    return total_score, priority, cat_match_label, reasoning

# LLM Outreach Generation
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

# Main Pipeline Execution
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
    name = raw_lead.get("name") or handle
    bio = raw_lead.get("bio") or ""
    website = raw_lead.get("website")
    followers = raw_lead.get("followers")
    is_verified = bool(raw_lead.get("is_verified"))
    email = raw_lead.get("email")
    email_source = raw_lead.get("email_source")
    phone = raw_lead.get("phone")
    captions = raw_lead.get("captions") or []
    scrape_status = raw_lead.get("scrape_status", "ok")
    error = raw_lead.get("error")

    # 1. Profile Analysis
    account_type = classify_account_type(bio, name, captions)
    primary_niche, secondary_niches = extract_niches(bio, captions, target_category)
    influence_level = get_influence_level(followers)

    # 2. Lead Scoring
    score, priority, category_match_desc, reasoning = compute_atlas_score(
        bio=bio,
        captions=captions,
        target_category=target_category,
        has_email=bool(email),
        has_phone=bool(phone),
        has_website=bool(website),
        is_verified=is_verified,
        influence_level=influence_level,
    )

    # 3. Outreach Generation (Only if score >= 50 / priority medium or high)
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
            "influence_level": influence_level,
            "engagement_metrics": {
                "follower_count": followers or 0,
                "avg_engagement_rate": None,
                "engagement_quality": "high" if is_verified or (email and website) else ("medium" if email or phone else "unknown"),
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
            "content_sentiment": "positive" if score >= 60 else "neutral",
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
