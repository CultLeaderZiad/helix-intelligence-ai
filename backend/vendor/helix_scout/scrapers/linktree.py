"""
Real Linktree Profile Scraper
Adapted from kiryano/Scout (MIT License)
"""
import re
import json
from typing import Dict, Any, Optional
import httpx
from .stealth import get_stealth_headers

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?[0-9]{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")

async def scrape_linktree_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real public Linktree profile data."""
    clean = handle.strip().lstrip("@").lower()
    url = f"https://linktr.ee/{clean}"
    
    try:
        resp = await client.get(url, headers=get_stealth_headers(), timeout=10.0)
        if resp.status_code == 404:
            return {
                "platform": "linktree",
                "handle": clean,
                "name": clean,
                "profile_url": url,
                "scrape_status": "not_found",
                "error": "profile_not_found",
            }
            
        if resp.status_code == 200:
            text = resp.text
            name = None
            bio = None
            email = None
            phone = None
            website = None
            socials = {}

            # 1. Parse __NEXT_DATA__ JSON hydration
            next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', text)
            if next_data_match:
                try:
                    nd = json.loads(next_data_match.group(1))
                    user_data = nd.get("props", {}).get("pageProps", {}) or {}
                    account = user_data.get("account", {}) or {}
                    name = account.get("pageTitle") or account.get("username")
                    bio = account.get("description")

                    # Check links
                    links = user_data.get("links", []) or []
                    for l in links:
                        link_url = l.get("url", "")
                        if "mailto:" in link_url:
                            em = link_url.replace("mailto:", "").split("?")[0].strip()
                            if EMAIL_REGEX.match(em):
                                email = em.lower()
                        elif "wa.me/" in link_url or "whatsapp.com" in link_url:
                            pm = re.search(r'(?:wa\.me/|phone=)(\+?[0-9]{8,15})', link_url)
                            if pm:
                                phone = pm.group(1)
                        elif not website and link_url.startswith("http") and "linktr.ee" not in link_url:
                            website = link_url

                    # Check social links
                    social_links = account.get("socialLinks", []) or []
                    for sl in social_links:
                        sl_type = sl.get("type")
                        sl_url = sl.get("url")
                        if sl_type and sl_url:
                            socials[sl_type] = sl_url
                except Exception:
                    pass

            # Fallback regex for bio and title
            if not name:
                title_match = re.search(r"<title>([^<]+)</title>", text)
                if title_match:
                    name = title_match.group(1).replace("| Linktree", "").strip()

            if not email:
                mailtos = re.findall(r'href=["\']mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)["\']', text)
                if mailtos:
                    email = mailtos[0].lower()

            if not phone:
                tel_match = re.search(r'href=["\'](?:tel:|https://wa\.me/)([^"\']+)["\']', text)
                if tel_match:
                    phone = tel_match.group(1).strip()

            return {
                "platform": "linktree",
                "handle": clean,
                "name": name or clean,
                "email": email,
                "email_source": "linktree_page" if email else None,
                "phone": phone,
                "phone_source": "linktree_whatsapp" if phone else None,
                "website": website or url,
                "bio": bio,
                "followers": None,
                "is_private": False,
                "captions": [],
                "profile_url": url,
                "scrape_status": "ok",
                "error": None,
            }
    except Exception as e:
        pass

    return {
        "platform": "linktree",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": url,
        "scrape_status": "needs_manual_review",
        "error": "linktree_fetch_failed",
    }
