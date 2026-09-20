"""
Real Pinterest Profile Scraper
Adapted from kiryano/Scout (MIT License)
"""
import re
from typing import Dict, Any
import httpx
from .stealth import get_stealth_headers

async def scrape_pinterest_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real public Pinterest profile."""
    clean = handle.strip().lstrip("@")
    url = f"https://www.pinterest.com/{clean}/"
    
    try:
        resp = await client.get(url, headers=get_stealth_headers(), timeout=10.0)
        if resp.status_code == 404:
            return {
                "platform": "pinterest",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": url,
                "scrape_status": "not_found",
                "error": "user_not_found",
            }
        if resp.status_code == 200:
            text = resp.text
            title_m = re.search(r"<title>([^<]+)</title>", text)
            name = title_m.group(1).split("on Pinterest")[0].strip() if title_m else clean
            
            desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', text)
            bio = desc_m.group(1) if desc_m else None
            
            return {
                "platform": "pinterest",
                "handle": clean,
                "name": name,
                "email": None,
                "email_source": None,
                "phone": None,
                "phone_source": None,
                "website": url,
                "bio": bio,
                "followers": None,
                "is_private": False,
                "captions": [],
                "profile_url": url,
                "scrape_status": "ok",
                "error": None,
            }
    except Exception:
        pass

    return {
        "platform": "pinterest",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": url,
        "scrape_status": "needs_manual_review",
        "error": "pinterest_fetch_failed",
    }
