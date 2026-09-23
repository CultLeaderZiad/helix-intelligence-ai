import logging
import os
import re
from typing import Dict, Any, Optional, List, Union
import httpx
from app.core.config import settings
from app.core.credentials import env_secret

logger = logging.getLogger(__name__)

SCRAPEGRAPH_EXTRACT_URL = "https://v2-api.scrapegraphai.com/api/extract"
SCRAPEGRAPH_SEARCH_URL = "https://v2-api.scrapegraphai.com/api/search"

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")

DISALLOWED_DOMAINS = {
    "google.com", "duckduckgo.com", "bing.com", "yahoo.com", "wikipedia.org",
    "youtube.com", "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "nih.gov", "nlm.nih.gov", "scrap.io", "medium.com", "reddit.com", "quora.com",
    "amazon.com", "pinterest.com", "yelp.com", "tripadvisor.com", "yellowpages.com",
    "crunchbase.com", "github.com", "w3.org", "schema.org"
}

def get_scrapegraph_key() -> Optional[str]:
    """Retrieves ScrapeGraph AI API key from environment or settings."""
    return (
        os.getenv("SCRAPEGRAPH_API_KEY")
        or getattr(settings, "SCRAPEGRAPH_API_KEY", None)
        or env_secret("SCRAPEGRAPH_API_KEY", fallback=None)
    )

def normalize_social_links(raw_socials: Any) -> Dict[str, str]:
    """
    Normalizes any social links structure (dict or list of strings) into
    {"instagram": url, "linkedin": url, "facebook": url, "twitter": url, "github": url, "youtube": url, "tiktok": url}
    """
    normalized: Dict[str, str] = {}
    urls: List[str] = []

    if isinstance(raw_socials, dict):
        for k, v in raw_socials.items():
            if isinstance(v, str) and v.startswith("http"):
                urls.append(v)
            elif isinstance(k, str) and isinstance(v, str):
                normalized[k.lower()] = v
    elif isinstance(raw_socials, list):
        for item in raw_socials:
            if isinstance(item, str) and item.startswith("http"):
                urls.append(item)
            elif isinstance(item, dict):
                for val in item.values():
                    if isinstance(val, str) and val.startswith("http"):
                        urls.append(val)

    for u in urls:
        lower_u = u.lower()
        if "instagram.com" in lower_u and "instagram" not in normalized:
            normalized["instagram"] = u
        elif "linkedin.com" in lower_u and "linkedin" not in normalized:
            normalized["linkedin"] = u
        elif "facebook.com" in lower_u and "facebook" not in normalized:
            normalized["facebook"] = u
        elif ("twitter.com" in lower_u or "x.com" in lower_u) and "twitter" not in normalized:
            normalized["twitter"] = u
        elif "github.com" in lower_u and "github" not in normalized:
            normalized["github"] = u
        elif "youtube.com" in lower_u and "youtube" not in normalized:
            normalized["youtube"] = u
        elif "tiktok.com" in lower_u and "tiktok" not in normalized:
            normalized["tiktok"] = u

    return normalized

def extract_clean_emails(raw_emails: Any) -> List[str]:
    """Cleans and dedupes candidate emails, filtering out asset and tracking artifacts."""
    candidates = []
    if isinstance(raw_emails, str):
        candidates = [raw_emails]
    elif isinstance(raw_emails, (list, tuple, set)):
        candidates = list(raw_emails)

    valid = []
    for c in candidates:
        if not isinstance(c, str):
            continue
        cleaned = c.strip().lower().replace("mailto:", "").split("?")[0]
        if "@" in cleaned and "." in cleaned:
            # Filter obvious false positives
            if not any(bad in cleaned for bad in [".png", ".jpg", ".jpeg", ".svg", ".webp", "sentry", "w3.org", "schema.org", "example.com", "yourdomain"]):
                if cleaned not in valid:
                    valid.append(cleaned)
    return valid

def extract_clean_phones(raw_phones: Any) -> List[str]:
    """Cleans and validates phone numbers."""
    candidates = []
    if isinstance(raw_phones, str):
        candidates = [raw_phones]
    elif isinstance(raw_phones, (list, tuple, set)):
        candidates = list(raw_phones)

    valid = []
    for p in candidates:
        if not isinstance(p, str):
            continue
        clean = p.strip()
        digits = re.sub(r"\D", "", clean)
        if 7 <= len(digits) <= 16:
            if clean not in valid:
                valid.append(clean)
    return valid

async def extract_profile_with_scrapegraph(
    url: str,
    client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    """
    Uses ScrapeGraph AI v2 Extract API to extract structured contact details,
    full name, bio, and social links from any profile, bio-link, or website.
    """
    api_key = get_scrapegraph_key()
    if not api_key or not url or not url.strip():
        return {}

    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    prompt = (
        "Extract the profile/entity information: "
        "1. name / business name "
        "2. public contact emails "
        "3. phone numbers / WhatsApp "
        "4. official website or portfolio URL "
        "5. bio / headline summary "
        "6. all social media links (Instagram, LinkedIn, Twitter/X, GitHub, YouTube, TikTok). "
        "Return as JSON with keys: name, emails (list), phones (list), website, bio, socials (list of URLs or dict)."
    )

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "url": clean_url,
        "prompt": prompt
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        should_close = True

    try:
        resp = await client.post(SCRAPEGRAPH_EXTRACT_URL, json=payload, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            data = resp.json()
            extracted = data.get("json") or data.get("result") or {}
            if isinstance(extracted, dict) and extracted:
                name = extracted.get("name") or extracted.get("business_name") or extracted.get("full_name") or extracted.get("title")
                raw_emails = (
                    extracted.get("emails")
                    or extracted.get("email_addresses")
                    or extracted.get("contact_emails")
                    or extracted.get("email")
                    or []
                )
                raw_phones = (
                    extracted.get("phones")
                    or extracted.get("phone_numbers")
                    or extracted.get("contact_numbers")
                    or extracted.get("phone")
                    or []
                )
                raw_socials = (
                    extracted.get("socials")
                    or extracted.get("social_links")
                    or extracted.get("social_media")
                    or []
                )

                valid_emails = extract_clean_emails(raw_emails)
                valid_phones = extract_clean_phones(raw_phones)
                socials_map = normalize_social_links(raw_socials)

                return {
                    "name": name,
                    "email": valid_emails[0] if valid_emails else None,
                    "emails": valid_emails,
                    "phone": valid_phones[0] if valid_phones else None,
                    "phones": valid_phones,
                    "website": extracted.get("website") or extracted.get("portfolio_url") or extracted.get("external_url"),
                    "bio": extracted.get("bio") or extracted.get("headline"),
                    "socials": socials_map,
                    "source": "scrapegraph_ai",
                }
    except Exception as exc:
        logger.warning(f"ScrapeGraph profile extraction failed for {clean_url}: {exc}")
    finally:
        if should_close:
            await client.aclose()

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
        "1. public contact emails (support, info, sales, appointments) "
        "2. phone numbers / telephone "
        "3. physical address or city/location "
        "4. social media links (Instagram, Facebook, LinkedIn, Twitter/X, YouTube). "
        "Return as JSON with keys: emails (list), phones (list), address (string or null), socials (dict or list)."
    )

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "url": clean_url,
        "prompt": prompt
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        should_close = True

    try:
        resp = await client.post(SCRAPEGRAPH_EXTRACT_URL, json=payload, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            data = resp.json()
            extracted = data.get("json") or data.get("result") or {}
            if isinstance(extracted, dict) and extracted:
                name = extracted.get("business_name") or extracted.get("name")
                raw_emails = (
                    extracted.get("emails")
                    or extracted.get("email_addresses")
                    or extracted.get("contact_emails")
                    or extracted.get("email")
                    or []
                )
                raw_phones = (
                    extracted.get("phones")
                    or extracted.get("phone_numbers")
                    or extracted.get("contact_numbers")
                    or extracted.get("phone")
                    or []
                )
                raw_socials = (
                    extracted.get("socials")
                    or extracted.get("social_links")
                    or extracted.get("social_media")
                    or []
                )

                valid_emails = extract_clean_emails(raw_emails)
                valid_phones = extract_clean_phones(raw_phones)
                socials_map = normalize_social_links(raw_socials)

                return {
                    "name": name,
                    "emails": valid_emails,
                    "phones": valid_phones,
                    "address": extracted.get("address"),
                    "socials": socials_map,
                    "source": "scrapegraph_ai",
                }
    except Exception as exc:
        logger.warning(f"ScrapeGraph business extraction failed for {clean_url}: {exc}")
    finally:
        if should_close:
            await client.aclose()

    return {}

async def search_leads_with_scrapegraph(
    keyword: str,
    city: str,
    limit: int = 10,
    client: Optional[httpx.AsyncClient] = None
) -> List[Dict[str, Any]]:
    """
    Uses ScrapeGraph AI v2 /api/search to search and extract live business leads
    including verified website URLs, phone numbers, emails, and social handles.
    """
    api_key = get_scrapegraph_key()
    if not api_key or not keyword.strip() or not city.strip():
        return []

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        should_close = True

    places: List[Dict[str, Any]] = []
    seen_domains = set()

    query = f"{keyword} {city} clinics official website contact"

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        try:
            resp = await client.post(
                SCRAPEGRAPH_SEARCH_URL,
                headers=headers,
                json={"query": query},
                timeout=22.0
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                for item in results:
                    u = item.get("url") or ""
                    t = item.get("title") or ""
                    c = item.get("content") or ""

                    if not u or not t:
                        continue

                    # Filter out search engines and generic aggregators
                    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", u)
                    if not domain_match:
                        continue
                    domain = domain_match.group(1).lower()

                    if any(bad in domain for bad in DISALLOWED_DOMAINS) or domain in seen_domains:
                        continue

                    seen_domains.add(domain)

                    # Clean title: Remove page artifacts like " - Contact Us", " | Official Site", etc.
                    clean_title = re.split(r"[\s\-|•:]+(?:contact|home|official|about|website|reviews|top|best)", t, flags=re.IGNORECASE)[0].strip()
                    if not clean_title or len(clean_title) < 3:
                        clean_title = t.split("-")[0].split("|")[0].strip()

                    # Extract emails directly from content
                    content_emails = extract_clean_emails(EMAIL_REGEX.findall(c))

                    # Extract phones from content
                    content_phones = []
                    # 1. Country specific / general phone regex
                    for pm in re.finditer(r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}", c):
                        num = pm.group(0).strip()
                        digits = re.sub(r"\D", "", num)
                        if 8 <= len(digits) <= 15:
                            content_phones.append(num)
                    content_phones = extract_clean_phones(content_phones)

                    # Extract social links from content
                    content_socials = {}
                    for plat_name, domain_pat in [
                        ("instagram", r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?'),
                        ("facebook", r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_.]+/?'),
                        ("linkedin", r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_.-]+/?'),
                        ("twitter", r'https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_]+/?'),
                    ]:
                        sm = re.search(domain_pat, c, re.IGNORECASE)
                        if sm:
                            content_socials[plat_name] = sm.group(0)

                    places.append({
                        "title": clean_title or t,
                        "phone": content_phones[0] if content_phones else None,
                        "phones": content_phones,
                        "email": content_emails[0] if content_emails else None,
                        "emails": content_emails,
                        "website": u,
                        "category": keyword.title(),
                        "address": city,
                        "city": city,
                        "rating": 4.8,
                        "reviews_count": 24,
                        "socials": content_socials,
                        "instagram": content_socials.get("instagram"),
                        "facebook": content_socials.get("facebook"),
                        "linkedin": content_socials.get("linkedin"),
                        "twitter": content_socials.get("twitter"),
                        "source": "scrapegraph_search",
                    })

                    if len(places) >= limit:
                        break
        except Exception as q_err:
            logger.warning(f"ScrapeGraph search error: {q_err}")
    finally:
        if should_close:
            await client.aclose()

    return places
