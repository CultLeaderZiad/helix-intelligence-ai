"""Entity Intelligence & Search Disambiguation Service.

Differentiates entities (Content Creators, Streamers, DTC Brands, SaaS, etc.)
and generates deep PR & marketing dossiers. Prunes false-positive phonetic
matches (e.g. shoe stores appearing under a search for Sneako) to protect
intelligence integrity.
"""

from __future__ import annotations

import logging
import json
import re
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

# Curated high-precision knowledge base for instant 0ms responses on key entities
KNOWN_ENTITIES: Dict[str, Dict[str, Any]] = {
    "sneako": {
        "entity_name": "Sneako (Nicolas Kenn De Balinthazy)",
        "entity_type": "creator_streamer",
        "category_label": "Content Creator & Streamer",
        "primary_platforms": ["Kick", "Rumble", "YouTube", "X (Twitter)"],
        "summary": "High-profile online creator, livestreamer, and commentator known for IRL streams, commentary, ideological debates, and multi-platform broadcasting.",
        "runs_direct_meta_ads": False,
        "marketing_archetype": "Controversy-Driven Organic Clipping & Multi-Platform Streaming",
        "online_presence": {
            "reach_overview": "Hundreds of thousands of concurrent livestream viewers and millions of organic short-form video impressions across social platforms.",
            "viral_engine": "Decentralized short-form clipping network (TikTok, YouTube Shorts, X) where fan channels syndicate livestream highlights.",
            "community_hubs": "Kick/Rumble live chat, X community spaces, Discord/Telegram subscriber groups."
        },
        "ad_and_monetization_footprint": {
            "strategy": "Does not run self-serve Meta product feed ads. Growth is powered by organic clip syndication and livestreams.",
            "primary_monetization": [
                "Exclusive multi-million dollar streaming contracts (Kick, Rumble)",
                "In-stream native live sponsor reads (VPNs, gaming, lifestyle, supplements)",
                "Affiliate marketing links & creator codes",
                "Direct merchandise drops and subscriber donations"
            ]
        },
        "disambiguation": {
            "has_confusion": True,
            "target_intent": "Sneako (Content Creator & Streamer)",
            "confused_with": "Footwear & Sneaker Retailers ('Sneakd Up', 'SNEAK O\\' KICKS', 'Sneakers')",
            "explanation": "Meta Ad Library's search algorithm stems 'sneako' to 'sneak', matching local sneaker and shoe stores. Helixa's relevance engine detected that Sneako is an online creator, not a shoe retailer, and pruned off-topic footwear ads.",
            "filtered_categories": ["Footwear", "Sneakers", "Shoe Sizing (e.g., sizes 41-45)", "Sneaker Resellers"]
        },
        "playbook_and_takeaways": [
            {
                "title": "Decentralized Clipping Syndicates",
                "detail": "Instead of paying Meta $40-$60 CPMs, top creators incentivize third-party clippers with affiliate bounties, generating tens of millions of views organically."
            },
            {
                "title": "Native In-Stream Sponsor Integration",
                "detail": "Live stream sponsors achieve 5-10x higher retention than static banner ads when the creator organically reviews or interacts with products during live broadcasts."
            },
            {
                "title": "Controversy & Algorithmic Velocity",
                "detail": "Polarized debate topics and high-friction discussions are used systematically to trigger algorithm recommendation loops on X and short-form video feeds."
            }
        ],
        "similar_entities": ["Andrew Tate", "Adin Ross", "Kai Cenat", "Vitaly", "Fresh & Fit"]
    },
    "andrew tate": {
        "entity_name": "Andrew Tate (Emory Andrew Tate III)",
        "entity_type": "creator_streamer",
        "category_label": "Media Personality & Entrepreneur",
        "primary_platforms": ["X (Twitter)", "Rumble", "Podcasts"],
        "summary": "Former kickboxer and controversial media personality known for Hustler's University / The Real World, luxury lifestyle marketing, and debate-heavy podcasts.",
        "runs_direct_meta_ads": False,
        "marketing_archetype": "Affiliate Army Syndication & High-Polarity PR",
        "online_presence": {
            "reach_overview": "Global notoriety driven by billions of organic short-form impressions through syndicated affiliate channels.",
            "viral_engine": "Multi-tier affiliate marketing model where members repost short-form clips with custom referral funnels.",
            "community_hubs": "The Real World network, Rumble streams, X/Twitter feed."
        },
        "ad_and_monetization_footprint": {
            "strategy": "Does not run direct-to-consumer Meta catalog ads under personal name due to platform policy restrictions.",
            "primary_monetization": [
                "Subscription education platform (The Real World / Hustler's University)",
                "Rumble streaming and media production",
                "Crypto, trading, and lifestyle ventures"
            ]
        },
        "disambiguation": {
            "has_confusion": True,
            "target_intent": "Andrew Tate (Media Personality)",
            "confused_with": "Unrelated brands with 'Andrew' or 'Tate' (e.g. automotive dealers, art galleries)",
            "explanation": "Ad libraries frequently match random local businesses containing common names. Helixa filters out non-affiliated entities.",
            "filtered_categories": ["Automotive", "Local Galleries", "Generic Consultancies"]
        },
        "playbook_and_takeaways": [
            {
                "title": "Commission-Driven Viral Distribution",
                "detail": "Outsourced marketing to thousands of student affiliates whose financial incentive was tied to clip performance."
            },
            {
                "title": "Aesthetic Lifestyle Framing",
                "detail": "Using hypercar visuals, cigar motifs, and aspirational luxury settings to maximize short-form hook rates."
            }
        ],
        "similar_entities": ["Tristan Tate", "Sneako", "Patrick Bet-David", "Jordan Peterson"]
    },
    "adin ross": {
        "entity_name": "Adin Ross",
        "entity_type": "creator_streamer",
        "category_label": "Livestreamer & Content Creator",
        "primary_platforms": ["Kick", "YouTube", "X (Twitter)"],
        "summary": "High-profile gaming and IRL livestreamer who transitioned from Twitch to an exclusive contract with Kick, hosting celebrity interviews and high-stakes games.",
        "runs_direct_meta_ads": False,
        "marketing_archetype": "Celebrity Collaboration & High-Stakes Streaming",
        "online_presence": {
            "reach_overview": "Tens of millions of followers across social platforms with top-tier livestream viewership.",
            "viral_engine": "High-profile celebrity and rapper collaborations turned into viral clips.",
            "community_hubs": "Kick streaming chat, Discord, X."
        },
        "ad_and_monetization_footprint": {
            "strategy": "Does not run Facebook/Meta feed ads. Monetization is direct platform equity/contracts and sponsor integrations.",
            "primary_monetization": [
                "Kick streaming contract and equity",
                "Gaming and betting partnerships",
                "Brand sponsorships and apparel"
            ]
        },
        "disambiguation": {
            "has_confusion": False,
            "target_intent": "Adin Ross (Streamer)",
            "confused_with": "Ross Stores / Generic Ross apparel",
            "explanation": "Filtered out apparel stores matching the surname 'Ross'.",
            "filtered_categories": ["Discount Retailers", "Apparel Stores"]
        },
        "playbook_and_takeaways": [
            {
                "title": "Cultural Crossover Collaborations",
                "detail": "Streaming with mainstream musicians, boxers, and political figures bridges disparate audience segments."
            }
        ],
        "similar_entities": ["Kai Cenat", "Sneako", "IShowSpeed", "xQc"]
    },
    "kai cenat": {
        "entity_name": "Kai Cenat",
        "entity_type": "creator_streamer",
        "category_label": "Livestreamer & Entertainer",
        "primary_platforms": ["Twitch", "YouTube", "X (Twitter)"],
        "summary": "Record-breaking Twitch streamer, Streamer of the Year, and cultural icon famous for 30-day subathons, celebrity marathons, and AMP group content.",
        "runs_direct_meta_ads": False,
        "marketing_archetype": "Event-Based Cultural Spectacle Streaming",
        "online_presence": {
            "reach_overview": "Top creator in global live entertainment with mainstream hip-hop and Hollywood crossovers.",
            "viral_engine": "High-energy comedic moments and unscripted celebrity visits syndicating across TikTok and Reels.",
            "community_hubs": "Twitch live chat, AMP YouTube channels."
        },
        "ad_and_monetization_footprint": {
            "strategy": "Does not run self-serve Meta ads. Major brands (Nike, McDonald's) partner with him for bespoke experiential campaigns.",
            "primary_monetization": [
                "Twitch subscriptions & creator revenue",
                "Enterprise brand endorsements (Nike partnership)",
                "YouTube monetization and merchandising"
            ]
        },
        "disambiguation": {
            "has_confusion": False,
            "target_intent": "Kai Cenat (Streamer & Entertainer)",
            "confused_with": "Phonetic matches",
            "explanation": "Filtered out unrelated apparel matches.",
            "filtered_categories": []
        },
        "playbook_and_takeaways": [
            {
                "title": "Eventized Marathons",
                "detail": "Turning streaming into episodic reality TV through themed set designs and surprise celebrity guests."
            }
        ],
        "similar_entities": ["Duke Dennis", "Fanum", "Adin Ross", "IShowSpeed"]
    }
}


def _heuristic_entity_classification(query: str) -> Dict[str, Any]:
    clean_q = (query or "").strip().lower()

    # 1. Exact match in curated list
    if clean_q in KNOWN_ENTITIES:
        return KNOWN_ENTITIES[clean_q]

    # 2. Check if known entity is inside query
    for k, profile in KNOWN_ENTITIES.items():
        if k in clean_q or clean_q in k:
            return profile

    # 3. Domain detection (e.g. nike.com, shopify.com)
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
                "explanation": f"Verified commercial domain query for '{domain_name}'.",
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
            "similar_entities": []
        }

    # 4. Fallback general entity profile
    title_q = query.strip().title()
    return {
        "entity_name": title_q,
        "entity_type": "general",
        "category_label": "Market Entity / Keyword",
        "primary_platforms": ["Digital & Social Channels"],
        "summary": f"Search intelligence for '{title_q}'. Monitored across Meta Ad Library, web presence, and digital marketing footprints.",
        "runs_direct_meta_ads": True,
        "marketing_archetype": "Multi-Channel Digital Marketing",
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

    # If in curated list, return immediately with highest precision
    low_q = clean_q.lower()
    if low_q in KNOWN_ENTITIES:
        return KNOWN_ENTITIES[low_q]

    # Check Groq LLM for dynamic classification
    api_key = env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)
    if not api_key:
        return _heuristic_entity_classification(clean_q)

    prompt = f"""You are an elite competitive intelligence & brand analyst for Helixa AI.
Analyze the entity searched by the user: "{clean_q}".

Determine:
1. Is this entity a Content Creator / Streamer / YouTuber / Influencer, or an E-Commerce / DTC Brand, or a SaaS / Software Company, or a general keyword?
2. Does this entity run self-serve product catalog ads on Meta (Facebook/Instagram), or is their marketing powered by organic platforms (Kick, Rumble, YouTube, X, TikTok) and in-stream sponsors?
3. What are common phonetic or semantic confusions that an ad library keyword search might erroneously return? (For example, searching for "Sneako" returns local sneaker/shoe stores like "Sneakd Up" or "SNEAK O' KICKS" because Meta stems "sneako" -> "sneak". If this is a creator, explicitly explain why footwear/shoe ads are irrelevant noise).
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
    "confused_with": "What ad libraries mistakenly match (e.g. Footwear stores)",
    "explanation": "Clear explanation of the phonetic stem mismatch",
    "filtered_categories": ["Footwear", "Sneakers"]
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
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
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
                        {"role": "user", "content": prompt}
                    ]
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "entity_name" in parsed:
                    return parsed
    except Exception as exc:
        logger.warning("Groq entity intelligence call failed or timed out: %s. Using heuristic fallback.", exc)

    return _heuristic_entity_classification(clean_q)
