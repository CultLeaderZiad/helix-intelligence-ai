"""
Real TikTok Profile Scraper
Adapted from kiryano/Scout (MIT License)
"""
import re
import json
from typing import Dict, Any
import httpx
from .stealth import get_stealth_headers

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

async def scrape_tiktok_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real public TikTok profile."""
    clean = handle.strip().lstrip("@")
    url = f"https://www.tiktok.com/@{clean}"
    
    try:
        resp = await client.get(url, headers=get_stealth_headers(), timeout=10.0)
        if resp.status_code == 404:
            return {
                "platform": "tiktok",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": url,
                "scrape_status": "not_found",
                "error": "user_not_found",
            }
            
        if resp.status_code == 200:
            text = resp.text
            name = clean
            bio = None
            followers = None
            website = None
            email = None

            # Check Universal Data
            match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">([^<]+)</script>', text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    user_info = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}) or {}
                    user = user_info.get("user", {}) or {}
                    stats = user_info.get("stats", {}) or {}
                    
                    name = user.get("nickname") or clean
                    bio = user.get("signature") or ""
                    followers = stats.get("followerCount")
                    website = user.get("bioLink", {}).get("link")
                except Exception:
                    pass

            if not bio:
                desc_m = re.search(r'<meta name="description" content="([^"]+)"', text)
                if desc_m:
                    bio = desc_m.group(1)

            if bio:
                em = EMAIL_REGEX.findall(bio)
                if em:
                    email = em[0].lower()

            return {
                "platform": "tiktok",
                "handle": clean,
                "name": name,
                "email": email,
                "email_source": "tiktok_bio" if email else None,
                "phone": None,
                "phone_source": None,
                "website": website,
                "bio": bio,
                "followers": followers,
                "is_private": False,
                "captions": [],
                "profile_url": url,
                "scrape_status": "ok",
                "error": None,
            }
    except Exception:
        pass

    return {
        "platform": "tiktok",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": url,
        "scrape_status": "needs_manual_review",
        "error": "tiktok_fetch_failed",
    }
