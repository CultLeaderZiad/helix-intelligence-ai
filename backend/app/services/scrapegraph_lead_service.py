import logging
import os
import re
from typing import Dict, Any, Optional, List
import httpx
from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

SCRAPEGRAPH_EXTRACT_URL = "https://v2-api.scrapegraphai.com/api/extract"

def get_scrapegraph_key() -> Optional[str]:
    """Retrieves ScrapeGraph AI API key from environment or settings."""
    return (
        os.getenv("SCRAPEGRAPH_API_KEY")
        or getattr(settings, "SCRAPEGRAPH_API_KEY", None)
        or env_secret("SCRAPEGRAPH_API_KEY", fallback=None)
    )

async def extract_profile_with_scrapegraph(
    url: str,
    client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    """
    Uses ScrapeGraph AI v2 Extract API to extract structured contact details,
    full name, bio, and social links from any profile, bio-link, or website.
    """
    api_key = get_scrapegraph_key()
    if not api_key:
        return {}

    if not url or not url.strip():
        return {}

    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    prompt = (
        "Extract the person or entity profile data: "
        "1. full name "
        "2. publicly listed contact emails (e.g. gmail, company email) "
        "3. phone numbers "
        "4. official website or portfolio URL "
        "5. bio or headline summary "
        "6. social profile links (Instagram, LinkedIn, Twitter/X, GitHub, YouTube, TikTok). "
        "Return as JSON with keys: name (string), emails (list of strings), phones (list of strings), "
        "website (string or null), bio (string or null), socials (dict of platform names to urls)."
    )

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "url": clean_url,
        "prompt": prompt
    }

    try:
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=25.0, follow_redirects=True)
            should_close = True

        try:
            resp = await client.post(SCRAPEGRAPH_EXTRACT_URL, json=payload, headers=headers, timeout=25.0)
            if resp.status_code == 200:
                data = resp.json()
                extracted = data.get("json") or data.get("result") or {}
                if isinstance(extracted, dict) and extracted:
                    # Clean emails
                    raw_emails = extracted.get("emails") or []
                    if isinstance(raw_emails, str):
                        raw_emails = [raw_emails]
                    valid_emails = [
                        e.strip().lower() for e in raw_emails
                        if isinstance(e, str) and "@" in e and not any(x in e.lower() for x in [".png", ".jpg", "sentry", "w3.org"])
                    ]

                    # Clean phones
                    raw_phones = extracted.get("phones") or []
                    if isinstance(raw_phones, str):
                        raw_phones = [raw_phones]
                    valid_phones = [p.strip() for p in raw_phones if isinstance(p, str) and len(p.strip()) >= 7]

                    return {
                        "name": extracted.get("name"),
                        "email": valid_emails[0] if valid_emails else None,
                        "emails": valid_emails,
                        "phone": valid_phones[0] if valid_phones else None,
                        "phones": valid_phones,
                        "website": extracted.get("website"),
                        "bio": extracted.get("bio"),
                        "socials": extracted.get("socials") or {},
                        "source": "scrapegraph_ai",
                    }
        finally:
            if should_close:
                await client.aclose()
    except Exception as exc:
        logger.warning(f"ScrapeGraph profile extraction failed for {clean_url}: {exc}")

    return {}

async def extract_business_with_scrapegraph(
    website_url: str,
    business_name: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    """
    Uses ScrapeGraph AI v2 Extract API to extract business contact emails,
    phone numbers, address, and social links from a business website.
    """
    api_key = get_scrapegraph_key()
    if not api_key or not website_url or not website_url.strip():
        return {}

    clean_url = website_url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    prompt = (
        f"Extract contact and social details for business '{business_name or 'Business'}': "
        "1. public contact emails (support, info, sales, general) "
        "2. phone numbers "
        "3. physical address or city/location "
        "4. social media links (Instagram, Facebook, LinkedIn, Twitter/X, YouTube). "
        "Return as JSON with keys: emails (list), phones (list), address (string or null), socials (dict)."
    )

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "url": clean_url,
        "prompt": prompt
    }

    try:
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=25.0, follow_redirects=True)
            should_close = True

        try:
            resp = await client.post(SCRAPEGRAPH_EXTRACT_URL, json=payload, headers=headers, timeout=25.0)
            if resp.status_code == 200:
                data = resp.json()
                extracted = data.get("json") or data.get("result") or {}
                if isinstance(extracted, dict) and extracted:
                    raw_emails = extracted.get("emails") or []
                    if isinstance(raw_emails, str):
                        raw_emails = [raw_emails]
                    valid_emails = [
                        e.strip().lower() for e in raw_emails
                        if isinstance(e, str) and "@" in e and not any(x in e.lower() for x in [".png", ".jpg", "sentry", "w3.org"])
                    ]

                    raw_phones = extracted.get("phones") or []
                    if isinstance(raw_phones, str):
                        raw_phones = [raw_phones]
                    valid_phones = [p.strip() for p in raw_phones if isinstance(p, str) and len(p.strip()) >= 7]

                    return {
                        "emails": valid_emails,
                        "phones": valid_phones,
                        "address": extracted.get("address"),
                        "socials": extracted.get("socials") or {},
                        "source": "scrapegraph_ai",
                    }
        finally:
            if should_close:
                await client.aclose()
    except Exception as exc:
        logger.warning(f"ScrapeGraph business extraction failed for {clean_url}: {exc}")

    return {}
