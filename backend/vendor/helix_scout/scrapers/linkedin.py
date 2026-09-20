"""
Real LinkedIn Profile Scraper (BYOK or Manual Review)
Adapted from kiryano/Scout (MIT License)
"""
import re
from typing import Dict, Any, Optional
import httpx
from .stealth import get_stealth_headers

async def scrape_linkedin_profile(handle: str, client: httpx.AsyncClient, cookie: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrapes real LinkedIn profile via BYOK session cookie.
    If no cookie configured, returns needs_manual_review status. Never fabricates leads.
    """
    clean = handle.strip().lstrip("@")
    url = f"https://www.linkedin.com/in/{clean}" if not clean.startswith("http") else clean

    if not cookie:
        return {
            "platform": "linkedin",
            "handle": clean,
            "name": clean,
            "email": None,
            "email_source": None,
            "phone": None,
            "phone_source": None,
            "website": None,
            "bio": None,
            "followers": None,
            "is_private": False,
            "captions": [],
            "profile_url": url,
            "scrape_status": "needs_manual_review",
            "error": "linkedin_requires_byok_cookie",
        }

    headers = get_stealth_headers()
    headers["Cookie"] = f"li_at={cookie}"

    try:
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            text = resp.text
            title_m = re.search(r"<title>([^<]+)</title>", text)
            name = title_m.group(1).split("-")[0].strip() if title_m else clean
            
            desc_m = re.search(r'<meta name="description" content="([^"]+)"', text)
            bio = desc_m.group(1) if desc_m else None

            return {
                "platform": "linkedin",
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
        "platform": "linkedin",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": url,
        "scrape_status": "needs_manual_review",
        "error": "linkedin_fetch_failed",
    }
