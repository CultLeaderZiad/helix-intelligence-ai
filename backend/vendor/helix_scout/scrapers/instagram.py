"""
Real Instagram Profile Scraper (No-Login, Zero Apify)
Adapted from kiryano/Scout (MIT License)
"""
import re
import json
from typing import Dict, Any, Optional
import httpx
from .stealth import get_stealth_headers

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?[0-9]{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")

async def scrape_instagram_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Scrapes real public Instagram profile data without login.
    Zero hallucination or fabrication. If rate-limited or private, returns status honestly.
    """
    clean = handle.strip().lstrip("@").lower()
    
    # Priority 1: Instagram Web Profile Info API
    api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={clean}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "x-ig-app-id": "936619743392459",
        "x-asbd-id": "129477",
        "x-requested-with": "XMLHttpRequest",
        "Referer": f"https://www.instagram.com/{clean}/",
    }
    
    try:
        resp = await client.get(api_url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            user = data.get("data", {}).get("user")
            if user:
                bio = user.get("biography") or ""
                full_name = user.get("full_name") or clean
                followers = user.get("edge_followed_by", {}).get("count")
                website = user.get("external_url")
                is_private = bool(user.get("is_private"))
                is_verified = bool(user.get("is_verified"))
                business_email = user.get("business_email")
                business_phone = user.get("business_phone_number")
                
                # Recent captions for topic extraction
                captions = []
                timeline = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
                for edge in timeline[:6]:
                    node = edge.get("node", {})
                    cap_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                    if cap_edges:
                        text = cap_edges[0].get("node", {}).get("text")
                        if text:
                            captions.append(text[:200])

                # Extract emails from bio or business_email
                email = business_email
                email_source = "business_email" if business_email else None
                if not email and bio:
                    found = EMAIL_REGEX.findall(bio)
                    if found:
                        email = found[0].lower()
                        email_source = "bio"

                phone = business_phone
                phone_source = "business_phone" if business_phone else None
                if not phone and bio:
                    tel_match = re.search(r'(?:wa\.me/|whatsapp:?\s*)(\+?[0-9]{8,15})', bio, re.IGNORECASE)
                    if tel_match:
                        phone = tel_match.group(1)
                        phone_source = "whatsapp_bio"

                scrape_status = "needs_manual_review" if is_private else "ok"

                return {
                    "platform": "instagram",
                    "handle": clean,
                    "name": full_name,
                    "email": email,
                    "email_source": email_source,
                    "phone": phone,
                    "phone_source": phone_source,
                    "website": website,
                    "bio": bio,
                    "followers": followers,
                    "is_private": is_private,
                    "is_verified": is_verified,
                    "captions": captions,
                    "profile_url": f"https://instagram.com/{clean}",
                    "scrape_status": scrape_status,
                    "error": None,
                }
        elif resp.status_code == 404:
            return {
                "platform": "instagram",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": f"https://instagram.com/{clean}",
                "scrape_status": "not_found",
                "error": "user_not_found",
            }
        elif resp.status_code in (401, 403, 429):
            # Fall through to meta tags
            pass
    except Exception:
        pass

    # Priority 2: Public HTML Meta Tags Fallback
    page_url = f"https://www.instagram.com/{clean}/"
    page_headers = get_stealth_headers()
    try:
        page_resp = await client.get(page_url, headers=page_headers, timeout=8.0)
        if page_resp.status_code == 404:
            return {
                "platform": "instagram",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": f"https://instagram.com/{clean}",
                "scrape_status": "not_found",
                "error": "user_not_found",
            }
        if page_resp.status_code == 200:
            html = page_resp.text
            desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            
            if desc_match:
                desc = desc_match.group(1)
                followers = None
                fol_m = re.search(r'([0-9.,KkMm]+)\s+Followers', desc)
                if fol_m:
                    fol_str = fol_m.group(1).lower().replace(",", "")
                    try:
                        if "k" in fol_str:
                            followers = int(float(fol_str.replace("k", "")) * 1000)
                        elif "m" in fol_str:
                            followers = int(float(fol_str.replace("m", "")) * 1000000)
                        else:
                            followers = int(float(fol_str))
                    except Exception:
                        followers = None

                name = clean
                if og_title:
                    raw = og_title.group(1).split("(@")[0].replace("• Instagram photos and videos", "").strip()
                    if raw:
                        name = raw

                # Extract email from description
                email = None
                em_list = EMAIL_REGEX.findall(desc)
                if em_list:
                    email = em_list[0].lower()

                return {
                    "platform": "instagram",
                    "handle": clean,
                    "name": name,
                    "email": email,
                    "email_source": "meta_bio" if email else None,
                    "phone": None,
                    "phone_source": None,
                    "website": None,
                    "bio": desc,
                    "followers": followers,
                    "is_private": False,
                    "is_verified": False,
                    "captions": [],
                    "profile_url": f"https://instagram.com/{clean}",
                    "scrape_status": "ok",
                    "error": None,
                }
    except Exception as e:
        pass

    # Honest failure status - never invent false leads
    return {
        "platform": "instagram",
        "handle": clean,
        "name": clean,
        "email": None,
        "email_source": None,
        "phone": None,
        "website": None,
        "bio": None,
        "followers": None,
        "is_private": False,
        "captions": [],
        "profile_url": f"https://instagram.com/{clean}",
        "scrape_status": "needs_manual_review",
        "error": "instagram_profile_protected_or_rate_limited",
    }
