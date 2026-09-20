"""
Real YouTube Channel Scraper
Adapted from kiryano/Scout (MIT License)
"""
import re
from typing import Dict, Any
import httpx
from .stealth import get_stealth_headers

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

async def scrape_youtube_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real YouTube channel metadata."""
    clean = handle.strip().lstrip("@")
    url = f"https://www.youtube.com/@{clean}"
    
    try:
        resp = await client.get(url, headers=get_stealth_headers(), timeout=10.0)
        if resp.status_code == 404:
            return {
                "platform": "youtube",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": url,
                "scrape_status": "not_found",
                "error": "channel_not_found",
            }
            
        if resp.status_code == 200:
            text = resp.text
            name = clean
            bio = None
            followers = None
            email = None

            # Title
            title_m = re.search(r'<meta property="og:title" content="([^"]+)"', text)
            if title_m:
                name = title_m.group(1).replace(" - YouTube", "").strip()

            # Description
            desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', text)
            if desc_m:
                bio = desc_m.group(1)

            # Subscribers count regex from page
            sub_m = re.search(r'([0-9.,KkMm]+)\s+subscribers', text)
            if sub_m:
                s_str = sub_m.group(1).lower().replace(",", "")
                try:
                    if "k" in s_str:
                        followers = int(float(s_str.replace("k", "")) * 1000)
                    elif "m" in s_str:
                        followers = int(float(s_str.replace("m", "")) * 1000000)
                    else:
                        followers = int(float(s_str))
                except Exception:
                    followers = None

            if bio:
                em = EMAIL_REGEX.findall(bio)
                if em:
                    email = em[0].lower()

            return {
                "platform": "youtube",
                "handle": clean,
                "name": name,
                "email": email,
                "email_source": "youtube_description" if email else None,
                "phone": None,
                "phone_source": None,
                "website": None,
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
        "platform": "youtube",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": url,
        "scrape_status": "needs_manual_review",
        "error": "youtube_fetch_failed",
    }
