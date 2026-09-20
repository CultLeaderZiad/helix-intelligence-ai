"""
Real Lead Enrichment (LeadEnricher)
Adapted from kiryano/Scout (MIT License)
"""
import re
from typing import Dict, Any, List, Optional
import httpx
from .stealth import get_stealth_headers

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

class LeadEnricher:
    """
    Crawls public websites and bio-links for verified contact details.
    Attribution: kiryano/Scout LeadEnricher (MIT License)
    """
    def __init__(self, hunter_api_key: Optional[str] = None, enable_smtp_verify: bool = False):
        self.hunter_api_key = hunter_api_key
        self.enable_smtp_verify = enable_smtp_verify

    async def enrich_from_website(self, website_url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        found_emails = set()
        found_phones = set()
        socials = {}

        if not website_url or not website_url.strip():
            return {"emails": [], "phones": [], "socials": {}, "email_source": None}

        url = website_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        targets = [url]
        base_domain = url.split("?")[0].rstrip("/")
        if base_domain.count("/") <= 3:
            targets.append(base_domain + "/contact")
            targets.append(base_domain + "/about")

        headers = get_stealth_headers()

        for target in targets:
            try:
                resp = await client.get(target, headers=headers, timeout=6.0)
                if resp.status_code == 200:
                    text = resp.text

                    # 1. Real mailto: links
                    mailtos = re.findall(r'href=["\']mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)["\']', text, re.IGNORECASE)
                    for m in mailtos:
                        clean_m = m.lower().split("?")[0]
                        if not any(ign in clean_m for ign in ["sentry", "w3.org", "schema.org", "example.com", ".png", ".jpg"]):
                            found_emails.add(clean_m)

                    # 2. General email regex
                    raw_emails = EMAIL_REGEX.findall(text)
                    for e in raw_emails:
                        lower_e = e.lower()
                        if not any(ign in lower_e for ign in ["sentry", "w3.org", "schema.org", "example.com", "yourdomain", ".png", ".jpg", ".svg", ".webp", ".gif", "bootstrap", "cloudflare", "fontawesome", "googleapis"]):
                            found_emails.add(lower_e)

                    # 3. Real tel: links
                    tels = re.findall(r'href=["\']tel:([^"\']+)["\']', text, re.IGNORECASE)
                    for t in tels:
                        clean_t = t.strip()
                        if len(clean_t) >= 7:
                            found_phones.add(clean_t)

                    # 4. Social media links
                    for plat_name, domain_pat in [
                        ("instagram", r'href=["\'](https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?)(?:["\']|$)'),
                        ("facebook", r'href=["\'](https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_.]+/?)(?:["\']|$)'),
                        ("linkedin", r'href=["\'](https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_.-]+/?)(?:["\']|$)'),
                        ("twitter", r'href=["\'](https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_]+/?)(?:["\']|$)'),
                    ]:
                        if plat_name not in socials:
                            sm = re.search(domain_pat, text, re.IGNORECASE)
                            if sm:
                                socials[plat_name] = sm.group(1).rstrip('"\'')
            except Exception:
                continue

        # Optional Hunter.io BYOK fallback
        if not found_emails and self.hunter_api_key and "://" in url:
            domain = url.split("://")[1].split("/")[0].replace("www.", "")
            try:
                h_url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={self.hunter_api_key}&limit=2"
                h_resp = await client.get(h_url, timeout=5.0)
                if h_resp.status_code == 200:
                    h_data = h_resp.json()
                    h_emails = h_data.get("data", {}).get("emails", [])
                    for he in h_emails:
                        val = he.get("value")
                        if val:
                            found_emails.add(val.lower())
            except Exception:
                pass

        emails_list = list(found_emails)
        phones_list = list(found_phones)

        return {
            "emails": emails_list,
            "phones": phones_list,
            "socials": socials,
            "email_source": "website_contact_page" if emails_list else None,
        }
