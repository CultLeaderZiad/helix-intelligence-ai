"""Competitor site snapshot: one public page of the advertiser's own website, nothing else.

The domain is the one the advertiser's ads in this workspace most often point to (never typed by the
user, so it cannot be aimed at an internal address; the fetch is SSRF-guarded anyway). We read the
home page once and keep: title, description, social links and links to pricing/about pages. Results
are cached per domain for a week and each user has a small daily allowance, so Render stays light.
Only what the page itself says is returned; nothing is guessed.
"""
from __future__ import annotations

import datetime
import re
import time
from collections import Counter
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from fastapi import HTTPException

from app.services.safe_fetch import UnsafeFetch, safe_http_get_async

CACHE_TTL_S = 7 * 24 * 3600
CACHE_MAX = 300
DAILY_LIMIT = 20
MAX_BYTES = 600_000
_cache: Dict[str, Any] = {}
_usage: Dict[str, Any] = {}

SOCIAL_HOSTS = {
    "facebook.com": "Facebook", "instagram.com": "Instagram", "tiktok.com": "TikTok", "youtube.com": "YouTube",
    "x.com": "X", "twitter.com": "X", "linkedin.com": "LinkedIn", "snapchat.com": "Snapchat",
    "pinterest.com": "Pinterest", "wa.me": "WhatsApp",
}
PAGE_WORDS = {"pricing": ("pricing", "prices", "plans", "الأسعار", "الاسعار"), "about": ("about", "من-نحن", "about-us"),
              "contact": ("contact", "اتصل", "تواصل"), "shop": ("shop", "store", "products", "collections")}


def _meta(html: str, *names: str) -> Optional[str]:
    for name in names:
        for pattern in (
            rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']*)["\']',
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']{re.escape(name)}["\']',
        ):
            m = re.search(pattern, html, re.I)
            if m and m.group(1).strip():
                return " ".join(unescape(m.group(1)).split())[:300]
    return None


def parse_home(html: str, base_url: str) -> Dict[str, Any]:
    """What the page says about itself. Pure function: no network."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = " ".join(unescape(title_m.group(1)).split())[:200] if title_m else None
    description = _meta(html, "description", "og:description")
    site_name = _meta(html, "og:site_name")
    host = (urlparse(base_url).hostname or "").lower()
    social: Dict[str, str] = {}
    pages: Dict[str, str] = {}
    for href in re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\']', html, re.I)[:400]:
        absolute = urljoin(base_url, href.strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        link_host = parsed.hostname.lower().removeprefix("www.")
        for domain, label in SOCIAL_HOSTS.items():
            if (link_host == domain or link_host.endswith("." + domain)) and label not in social and parsed.path.strip("/"):
                social[label] = absolute[:300]
        if link_host == host.removeprefix("www."):
            low = parsed.path.lower()
            for key, words in PAGE_WORDS.items():
                if key not in pages and any(w in low for w in words):
                    pages[key] = absolute[:300]
    return {"title": title, "description": description, "site_name": site_name, "social": social, "pages": pages}


def _check_allowance(user_id: str) -> None:
    today = datetime.date.today().isoformat()
    day, count = _usage.get(user_id, (today, 0))
    if day != today:
        count = 0
    if count >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail={
            "code": "snapshot_daily_limit", "message": f"You can look up {DAILY_LIMIT} competitor sites per day. Try again tomorrow.",
        })
    if len(_usage) > 5000:
        _usage.clear()
    _usage[user_id] = (today, count + 1)


def top_domain(domains: List[Optional[str]]) -> Optional[str]:
    from app.services.creative_fingerprint import normalize_domain

    counts = Counter(d for d in (normalize_domain(x) for x in domains if x) if d and "." in d and " " not in d)
    return counts.most_common(1)[0][0] if counts else None


async def snapshot(user_id: str, domain: Optional[str]) -> Dict[str, Any]:
    if not domain:
        raise HTTPException(status_code=404, detail={
            "code": "snapshot_no_site", "message": "None of this advertiser's ads point to a website we can read.",
        })
    hit = _cache.get(domain)
    if hit and time.monotonic() - hit["at"] < CACHE_TTL_S:
        return {**hit["data"], "cached": True}
    _check_allowance(user_id)
    url = f"https://{domain}/"
    try:
        resp = await safe_http_get_async(url, timeout=8.0, max_redirects=3, max_bytes=MAX_BYTES,
                                         headers={"User-Agent": "HelixBot/1.0 (+public page, one request)", "Accept": "text/html"})
    except (UnsafeFetch, OSError, ValueError):
        raise HTTPException(status_code=502, detail={"code": "snapshot_unreachable", "message": "The site could not be reached."})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "snapshot_unreachable", "message": "The site could not be reached."})
    ctype = str(resp.headers.get("content-type", "")).lower()
    if resp.status_code >= 400 or "html" not in ctype:
        raise HTTPException(status_code=502, detail={"code": "snapshot_unreadable", "message": "The site did not return a readable page."})
    html = resp.content[:MAX_BYTES].decode(resp.encoding or "utf-8", errors="replace")
    data = {"domain": domain, "url": url, **parse_home(html, str(getattr(resp, "url", url))),
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "cached": False}
    if len(_cache) >= CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[domain] = {"at": time.monotonic(), "data": data}
    return data
