"""Entity classification for a search the caller typed.

There is no curated brand or person list. With a model key, the dossier is
built from that query. Without one, the result is a generic heuristic and is
labeled as such.
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

def _drop_unfetched_urls(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Keep a handle for display, but do not ship a URL that was not fetched."""
    copied = dict(profile)
    links = copied.get("social_links") or {}
    cleaned: Dict[str, Dict[str, Any]] = {}
    if isinstance(links, dict):
        for key, entry in links.items():
            if not isinstance(entry, dict):
                continue
            fetched = entry.get("fetched") is True
            cleaned[str(key)] = {
                "name": entry.get("name") or key,
                "handle": entry.get("handle"),
                "profile_url": entry.get("profile_url") if fetched else None,
                "search_url": entry.get("search_url") if fetched else None,
                "fetched": fetched,
            }
    copied["social_links"] = cleaned
    return copied


def _heuristic_entity_classification(query: str) -> Dict[str, Any]:
    clean_q = (query or "").strip().lower()

    # A domain-shaped query describes whatever the caller typed. Nothing here
    # names a built-in brand, person, or sample search.
    if "." in clean_q and " " not in clean_q:
        domain_name = clean_q.split("://")[-1].split("/")[0].replace("www.", "")
        brand_label = domain_name.split(".")[0].title()
        return {
            "entity_name": brand_label,
            "entity_type": "ecommerce_brand",
            "category_label": "Direct-to-Consumer / E-Commerce Brand",
            "primary_platforms": ["Meta (Facebook/Instagram)", "Google", "TikTok"],
            "summary": f"Commercial brand operating via primary domain '{domain_name}'. Runs direct-response and brand awareness ad campaigns.",
            "runs_direct_meta_ads": True,
            "marketing_archetype": "Performance Paid Traffic & Funnel Conversion",
            "online_presence": {
                "reach_overview": f"E-commerce storefront at {domain_name}.",
                "viral_engine": "Paid social advertising, email retention flows, retargeting funnels.",
                "community_hubs": "Brand website, customer reviews, social brand pages."
            },
            "ad_and_monetization_footprint": {
                "strategy": "Runs direct-response product catalog ads on Meta driving users to checkout.",
                "primary_monetization": ["Direct product sales", "Subscriptions", "Customer lifetime value"]
            },
            "disambiguation": {
                "has_confusion": False,
                "target_intent": f"{brand_label} Official Brand",
                "confused_with": "",
                "explanation": f"Domain-shaped query for '{domain_name}'. Not a fetched profile.",
                "filtered_categories": []
            },
            "playbook_and_takeaways": [
                {
                    "title": "Direct-Response Creative Hooks",
                    "detail": "Test first 3-second visual hooks highlighting user pain points before presenting the product solution."
                },
                {
                    "title": "Retargeting & Abandoned Cart Loops",
                    "detail": "Combine Meta dynamic ads with automated SMS/email sequences to recover drop-offs."
                }
            ],
            "similar_entities": [],
            "social_links": {},
        }

    # 4. Fallback general entity profile
    title_q = query.strip().title()
    return {
        "entity_name": title_q,
        "entity_type": "general",
        "category_label": "Market Entity / Keyword",
        "primary_platforms": [],
        "summary": f"Search intelligence for '{title_q}'. Monitored across Meta Ad Library, web presence, and digital marketing footprints.",
        "runs_direct_meta_ads": None,
        "marketing_archetype": "Multi-Channel Digital Marketing",
        "social_links": {},
        "online_presence": {
            "reach_overview": f"Digital footprint across social platforms and search engines for {title_q}.",
            "viral_engine": "Content publishing and paid ad creative.",
            "community_hubs": "Social media channels and web presence."
        },
        "ad_and_monetization_footprint": {
            "strategy": f"Analyzed for commercial ads and creative campaigns associated with {title_q}.",
            "primary_monetization": ["Product sales, brand sponsorships, and commercial services."]
        },
        "disambiguation": {
            "has_confusion": False,
            "target_intent": title_q,
            "confused_with": "",
            "explanation": "Direct semantic search.",
            "filtered_categories": []
        },
        "playbook_and_takeaways": [
            {
                "title": "Audience Hook Testing",
                "detail": "Identify the top resonant copy angles and creative formats within this category."
            },
            {
                "title": "Platform Diversification",
                "detail": "Scale high-performing ad concepts across both vertical video and carousel formats."
            }
        ],
        "similar_entities": []
    }


async def analyze_entity_intent(query: str, raw_creatives: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Classify the search query entity and generate a strategic PR & marketing dossier.

    Determines if the query is a content creator / streamer (who does not run direct Meta ads)
    or an e-commerce brand (who does), and identifies phonetic confusions to filter out.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        return _heuristic_entity_classification("Unknown")

    # No curated dossier. A model call, when a key is configured, classifies
    # only the caller's query. Otherwise the heuristic below is unlabeled.
    # Check Groq LLM for dynamic classification
    api_key = env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)
    if not api_key:
        heuristic = dict(_heuristic_entity_classification(clean_q))
        heuristic.setdefault("evidence_status", "unverified_heuristic")
        heuristic.setdefault("evidence_label", "Heuristic hypothesis. Not fetched from an ad library.")
        return _drop_unfetched_urls(heuristic)

    prompt = f"""You are an elite competitive intelligence & brand analyst for Helixa AI.
Analyze the entity searched by the user: "{clean_q}".

Determine:
1. Is this entity a Content Creator / Streamer / YouTuber / Influencer, or an E-Commerce / DTC Brand, or a SaaS / Software Company, or a general keyword?
2. Does this entity run self-serve product catalog ads on Meta (Facebook/Instagram), or is their marketing powered by organic platforms (Kick, Rumble, YouTube, X, TikTok) and in-stream sponsors?
3. What unrelated categories could a keyword search confuse with this query because of stemming or a shared word? Name categories, not example brands. If the query is a person, say which product categories are noise.
4. Provide a structured PR & marketing playbook for this entity.

Respond ONLY with valid JSON matching this schema:
{{
  "entity_name": "Full recognizable name",
  "entity_type": "creator_streamer" | "ecommerce_brand" | "saas_tech" | "public_figure" | "general",
  "category_label": "e.g. Content Creator & Streamer",
  "primary_platforms": ["Platform1", "Platform2"],
  "summary": "2-3 sentence overview of who this entity is and what they do",
  "runs_direct_meta_ads": false,
  "marketing_archetype": "Short descriptor of their growth style",
  "online_presence": {{
    "reach_overview": "Summary of their audience and reach",
    "viral_engine": "How they achieve organic viral distribution",
    "community_hubs": "Where their audience gathers"
  }},
  "ad_and_monetization_footprint": {{
    "strategy": "Why they do or do not run Meta ads, and how they convert attention",
    "primary_monetization": ["Revenue stream 1", "Revenue stream 2", "Revenue stream 3"]
  }},
  "disambiguation": {{
    "has_confusion": true,
    "target_intent": "What the user actually searched for",
    "confused_with": "The unrelated category a keyword search might return",
    "explanation": "Why those results are not this query",
    "filtered_categories": ["category to drop"]
  }},
  "playbook_and_takeaways": [
    {{
      "title": "Strategy 1 Title",
      "detail": "Tactical explanation of the strategy"
    }},
    {{
      "title": "Strategy 2 Title",
      "detail": "Tactical explanation of the strategy"
    }}
  ],
  "similar_entities": ["Entity 1", "Entity 2"]
}}"""

    try:
        from app.services.safe_fetch import safe_request_async
        resp = await safe_request_async(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            timeout=4.0,
            allowed_hosts={"api.groq.com"},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are Helixa AI's entity intelligence engine. Output only strictly valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            },
        )

        if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "entity_name" in parsed:
                    from app.services.ai.structured import InvalidModelOutput, parse_entity
                    try:
                        labeled = parse_entity(parsed)
                    except InvalidModelOutput:
                        labeled = None
                    if labeled:
                        labeled["prompt_version"] = "entity-dossier-v2"
                        labeled["model"] = "llama-3.1-8b-instant"
                        return _drop_unfetched_urls(labeled)
    except Exception as exc:
        logger.warning("Groq entity intelligence call failed or timed out: %s. Using heuristic fallback.", exc)

    heuristic = dict(_heuristic_entity_classification(clean_q))
    heuristic["evidence_status"] = "unverified_heuristic"
    heuristic["evidence_label"] = "Heuristic hypothesis. Not fetched from an ad library."
    heuristic["social_links"] = {}
    return _drop_unfetched_urls(heuristic)
