"""
Helix Scout OSS Package
Adapted from kiryano/Scout (MIT License)
Real scrapers, stealth headers, proxy rotation, and LeadEnricher.
"""

from .scrapers.stealth import get_stealth_headers, get_scout_proxy
from .scrapers.instagram import scrape_instagram_profile
from .scrapers.linktree import scrape_linktree_profile
from .scrapers.github import scrape_github_profile
from .scrapers.tiktok import scrape_tiktok_profile
from .scrapers.youtube import scrape_youtube_profile
from .scrapers.linkedin import scrape_linkedin_profile
from .scrapers.pinterest import scrape_pinterest_profile
from .scrapers.twitch import scrape_twitch_profile
from .scrapers.enrichment import LeadEnricher

__all__ = [
    "get_stealth_headers",
    "get_scout_proxy",
    "scrape_instagram_profile",
    "scrape_linktree_profile",
    "scrape_github_profile",
    "scrape_tiktok_profile",
    "scrape_youtube_profile",
    "scrape_linkedin_profile",
    "scrape_pinterest_profile",
    "scrape_twitch_profile",
    "LeadEnricher",
]
