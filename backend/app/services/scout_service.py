import os
import re
import asyncio
import time
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.scout import ScoutJob, ScoutLead
from app.models.organization import Organization
from app.db.session import async_session_maker

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?[0-9]{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

URL_PATTERNS = [
    ("instagram", re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/(?:p/|reel/)?([a-zA-Z0-9_.]+)/?")),
    ("linkedin", re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)/?")),
    ("tiktok", re.compile(r"(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]+)/?")),
    ("youtube", re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/(?:@|c/|channel/|user/)?([a-zA-Z0-9_.-]+)/?")),
    ("github", re.compile(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/?")),
    ("linktree", re.compile(r"(?:https?://)?(?:www\.)?linktr\.ee/([a-zA-Z0-9_.]+)/?")),
    ("twitch", re.compile(r"(?:https?://)?(?:www\.)?twitch\.tv/([a-zA-Z0-9_]+)/?")),
    ("pinterest", re.compile(r"(?:https?://)?(?:www\.)?pinterest\.com/([a-zA-Z0-9_]+)/?")),
    ("x", re.compile(r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)/?")),
]

def parse_scout_input(raw_lines: List[str], fallback_platforms: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses input lines (handles or profile URLs).
    Rejects handles with spaces.
    Returns (valid_targets, errors).
    """
    targets = []
    errors = []
    seen = set()

    for line in raw_lines:
        clean = line.strip()
        if not clean:
            continue

        matched_url = False
        for plat, pat in URL_PATTERNS:
            m = pat.search(clean)
            if m:
                h = m.group(1).strip().lstrip("@")
                if " " in h or "\t" in h:
                    errors.append(f"Handle in URL '{clean}' contains invalid whitespace")
                    matched_url = True
                    break
                key = (plat, h.lower())
                if key not in seen:
                    seen.add(key)
                    targets.append({
                        "platform": plat,
                        "handle": h,
                        "profile_url": clean if clean.startswith("http") else f"https://{clean}",
                    })
                matched_url = True
                break

        if matched_url:
            continue

        if clean.startswith("http://") or clean.startswith("https://") or "www." in clean:
            errors.append(f"Unrecognized profile URL domain: '{clean}'")
            continue

        # Bare handle
        h = clean.lstrip("@").strip()
        if " " in h or "\t" in h:
            errors.append(f"Handle '{clean}' contains invalid whitespace")
            continue

        if not re.match(r"^[a-zA-Z0-9_.-]+$", h):
            errors.append(f"Handle '{clean}' contains illegal characters")
            continue

        fallback = [p.lower() for p in fallback_platforms] if fallback_platforms else ["github", "linktree", "instagram"]
        for p in fallback:
            key = (p, h.lower())
            if key not in seen:
                seen.add(key)
                targets.append({
                    "platform": p,
                    "handle": h,
                    "profile_url": None,
                })

    return targets, errors

async def enrich_from_website(website_url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Scrapes real contact info & socials from a website homepage and /contact page.
    Zero hallucination or fabrication.
    """
    found_emails = set()
    found_phones = set()
    socials = {}

    if not website_url or not website_url.strip():
        return {"emails": [], "phones": [], "socials": {}}

    url = website_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    targets = [url]
    base_domain = url.split("?")[0].rstrip("/")
    if base_domain.count("/") <= 3:
        targets.append(base_domain + "/contact")
        targets.append(base_domain + "/about")

    for target in targets:
        try:
            resp = await client.get(target, headers=HEADERS, timeout=6.0)
            if resp.status_code == 200:
                text = resp.text

                # 1. Real mailto: links
                mailtos = re.findall(r'href=["\']mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)["\']', text, re.IGNORECASE)
                for m in mailtos:
                    clean_m = m.lower()
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

    return {
        "emails": list(found_emails),
        "phones": list(found_phones),
        "socials": socials,
    }

async def scrape_github_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real public GitHub profile and commit event email."""
    url = f"https://api.github.com/users/{handle}"
    try:
        resp = await client.get(url, headers={"User-Agent": "Helix-Scout/1.0", "Accept": "application/vnd.github.v3+json"}, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("email")
            # If email is null, check public commit events
            if not email:
                try:
                    events_resp = await client.get(f"https://api.github.com/users/{handle}/events/public", headers={"User-Agent": "Helix-Scout/1.0"}, timeout=6.0)
                    if events_resp.status_code == 200:
                        events = events_resp.json()
                        for event in events[:5]:
                            if event.get("type") == "PushEvent":
                                commits = event.get("payload", {}).get("commits", [])
                                for commit in commits:
                                    c_email = commit.get("author", {}).get("email")
                                    if c_email and "noreply" not in c_email and "@" in c_email:
                                        email = c_email
                                        break
                                if email:
                                    break
                except Exception:
                    pass

            return {
                "name": data.get("name") or handle,
                "email": email,
                "website": data.get("blog") or (f"https://github.com/{handle}"),
                "bio": data.get("bio") or f"GitHub developer with {data.get('public_repos', 0)} public repos",
                "followers": data.get("followers", 0),
                "phone": None,
                "profile_url": f"https://github.com/{handle}",
                "email_source": "github_commits" if email and not data.get("email") else ("github_profile" if email else None),
            }
        elif resp.status_code == 404:
            return {"error": "user_not_found"}
        else:
            return {"error": f"github_api_status_{resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

async def scrape_linktree_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real Linktree page text, links, and contact buttons."""
    url = f"https://linktr.ee/{handle}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=8.0, follow_redirects=True)
        if resp.status_code == 200:
            html = resp.text
            # Extract name
            name_match = re.search(r"<title>([^<]+)</title>", html)
            raw_title = name_match.group(1) if name_match else handle
            name = raw_title.replace("| Linktree", "").replace("@", "").strip()

            # Extract bio
            bio_match = re.search(r'<meta name="description" content="([^"]+)"', html)
            bio = bio_match.group(1).strip() if bio_match else f"Linktree profile for @{handle}"

            # Extract real email
            emails = EMAIL_REGEX.findall(html)
            email = None
            for e in emails:
                if not any(ign in e.lower() for ign in ["sentry", "w3.org", "schema.org", "linktree", "github", "example"]):
                    email = e
                    break

            # Check outbound website
            website = None
            url_matches = re.findall(r'href="(https?://[^"]+)"', html)
            for u in url_matches:
                if not any(ign in u.lower() for ign in ["linktr.ee", "google", "apple", "facebook", "twitter", "instagram", "tiktok"]):
                    website = u
                    break

            # Phone / WhatsApp
            phone = None
            wa_match = re.search(r'href="https?://wa\.me/(\+?[0-9]+)"', html)
            if wa_match:
                phone = f"+{wa_match.group(1).lstrip('+')}"
            else:
                tel_match = re.search(r'href="tel:([^"]+)"', html)
                if tel_match:
                    phone = tel_match.group(1)

            return {
                "name": name or handle,
                "email": email,
                "website": website or url,
                "bio": bio,
                "followers": None,  # Real: Linktree has no public follower count
                "phone": phone,
                "profile_url": url,
                "email_source": "linktree_bio" if email else None,
                "phone_source": "whatsapp_button" if phone else None,
            }
        elif resp.status_code == 404:
            return {"error": "profile_not_found"}
        else:
            return {"error": f"linktree_status_{resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

async def scrape_instagram_profile(handle: str, client: httpx.AsyncClient, apify_token: Optional[str] = None) -> Dict[str, Any]:
    """Scrapes real Instagram profile via Apify or public meta tags. Never invents leads."""
    clean = handle.strip().lstrip("@")
    
    # Priority 1: Apify Instagram Actor
    token = apify_token or os.environ.get("APIFY_API_TOKEN")
    if token:
        try:
            apify_url = f"https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items?token={token}"
            resp = await client.post(apify_url, json={"usernames": [clean]}, timeout=25.0)
            if resp.status_code in (200, 201):
                items = resp.json()
                if items and isinstance(items, list) and len(items) > 0:
                    profile = items[0]
                    email = profile.get("email") or profile.get("businessEmail")
                    phone = profile.get("phone") or profile.get("businessPhone")
                    website = profile.get("externalUrl")
                    bio = profile.get("biography")
                    followers = profile.get("followersCount")
                    name = profile.get("fullName") or clean
                    return {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "website": website,
                        "bio": bio,
                        "followers": followers,
                        "profile_url": f"https://instagram.com/{clean}",
                        "email_source": "instagram_business" if email else None,
                        "phone_source": "instagram_business" if phone else None,
                    }
        except Exception:
            pass

    # Priority 2: Public meta tags
    url = f"https://www.instagram.com/{clean}/"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=8.0)
        if resp.status_code == 404:
            return {"error": "user_not_found"}
        if resp.status_code == 200:
            html = resp.text
            desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if desc_match:
                content = desc_match.group(1)
                followers = None
                fol_m = re.search(r'([0-9.,KkMm]+)\s+Followers', content)
                if fol_m:
                    fol_str = fol_m.group(1).lower().replace(",", "")
                    try:
                        if "k" in fol_str:
                            followers = int(float(fol_str.replace("k", "")) * 1000)
                        elif "m" in fol_str:
                            followers = int(float(fol_str.replace("m", "")) * 1000000)
                        else:
                            followers = int(fol_str)
                    except Exception:
                        followers = None

                name = clean
                if og_title:
                    raw = og_title.group(1).split("(@")[0].replace("• Instagram photos and videos", "").strip()
                    if raw:
                        name = raw

                # Look for email in description
                email = None
                em_list = EMAIL_REGEX.findall(content)
                if em_list:
                    email = em_list[0]

                return {
                    "name": name,
                    "email": email,
                    "phone": None,
                    "website": None,
                    "bio": content,
                    "followers": followers,
                    "profile_url": f"https://instagram.com/{clean}",
                    "email_source": "instagram_bio" if email else None,
                }
    except Exception:
        pass

    return {"error": "instagram_requires_auth_or_apify_token"}

async def scrape_linkedin_profile(handle: str, client: httpx.AsyncClient, cookie: Optional[str] = None) -> Dict[str, Any]:
    """Scrapes real LinkedIn profile via BYOK session cookie. Never fabricates."""
    clean = handle.strip().lstrip("@")
    if not cookie:
        return {"error": "linkedin_requires_byok_cookie (configure in Scout Settings)"}

    headers = {
        **HEADERS,
        "Cookie": f"li_at={cookie}",
        "csrf-token": "ajax:none",
        "x-restli-protocol-version": "2.0.0",
    }
    url = f"https://www.linkedin.com/voyager/api/identity/profiles/{clean}/profileView"
    try:
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            profile = data.get("profile", {})
            first = profile.get("firstName", "")
            last = profile.get("lastName", "")
            name = f"{first} {last}".strip() or clean
            headline = profile.get("headline")
            summary = profile.get("summary") or headline
            return {
                "name": name,
                "email": None,
                "phone": None,
                "website": f"https://linkedin.com/in/{clean}",
                "bio": summary,
                "followers": None,
                "profile_url": f"https://linkedin.com/in/{clean}",
                "email_source": None,
            }
        elif resp.status_code in (401, 403):
            return {"error": "linkedin_cookie_invalid_or_expired"}
        elif resp.status_code == 404:
            return {"error": "user_not_found"}
        else:
            return {"error": f"linkedin_api_status_{resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

async def scrape_tiktok_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real TikTok profile page meta. Never invents leads."""
    clean = handle.strip().lstrip("@")
    url = f"https://www.tiktok.com/@{clean}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=8.0)
        if resp.status_code == 200:
            html = resp.text
            bio_m = re.search(r'<meta name="description" content="([^"]+)"', html)
            title_m = re.search(r'<title>([^<]+)</title>', html)
            name = title_m.group(1).split("(@")[0].strip() if title_m else clean
            bio = bio_m.group(1) if bio_m else None
            email = None
            if bio:
                em = EMAIL_REGEX.findall(bio)
                if em:
                    email = em[0]
            return {
                "name": name,
                "email": email,
                "phone": None,
                "website": url,
                "bio": bio,
                "followers": None,
                "profile_url": url,
                "email_source": "tiktok_bio" if email else None,
            }
        elif resp.status_code == 404:
            return {"error": "user_not_found"}
    except Exception:
        pass
    return {"error": "tiktok_scraping_restricted_or_not_found"}

async def scrape_youtube_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real YouTube channel meta. Never invents leads."""
    clean = handle.strip().lstrip("@")
    url = f"https://www.youtube.com/@{clean}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=8.0)
        if resp.status_code == 200:
            html = resp.text
            desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
            title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            name = title_m.group(1) if title_m else clean
            bio = desc_m.group(1) if desc_m else None
            email = None
            if bio:
                em = EMAIL_REGEX.findall(bio)
                if em:
                    email = em[0]
            return {
                "name": name,
                "email": email,
                "phone": None,
                "website": url,
                "bio": bio,
                "followers": None,
                "profile_url": url,
                "email_source": "youtube_about" if email else None,
            }
        elif resp.status_code == 404:
            return {"error": "channel_not_found"}
    except Exception:
        pass
    return {"error": "youtube_scraping_restricted"}

def compute_lead_score(email: Optional[str], phone: Optional[str], website: Optional[str], bio: Optional[str], followers: Optional[int]) -> int:
    """Computes lead score strictly based on discovered real fields."""
    score = 25  # base presence
    if email:
        score += 35
    if phone:
        score += 20
    if website and "http" in website:
        score += 10
    if bio and len(bio) > 15:
        score += 5
    if followers and followers > 1000:
        score += 5
    return min(score, 100)

async def run_scout_job_worker(job_id: str):
    """
    Background worker for Social Scout jobs.
    Only stores verified leads. Never creates fake leads.
    """
    async with async_session_maker() as db:
        res = await db.execute(select(ScoutJob).where(ScoutJob.id == job_id))
        job = res.scalars().first()
        if not job:
            return

        # Fetch organization for BYOK keys
        org_res = await db.execute(select(Organization).where(Organization.id == job.org_id))
        org = org_res.scalars().first()
        flags = (org.custom_feature_flags if org else {}) or {}
        linkedin_cookie = flags.get("linkedin_cookie") or flags.get("linkedin_byok_cookie")
        hunter_key = flags.get("hunter_api_key") or os.environ.get("HUNTER_API_KEY")
        apify_token = os.environ.get("APIFY_API_TOKEN")

        job.status = "running"
        job.stage = "init"
        job.stage_label = "Parsing and validating input targets"
        job.stage_index = 1
        job.stages_total = 4
        job.logs = [
            "> engine: helix_scout/v1 (real provider pipeline) · ok",
            f"> apify: {'configured' if apify_token else 'off'} · linkedin_byok: {'configured' if linkedin_cookie else 'off'}",
        ]
        job.heartbeat_at = datetime.now(timezone.utc)
        await db.commit()

        start_time = time.time()
        logs = list(job.logs)

        # Parse handles and profile URLs
        targets, parse_errors = parse_scout_input(job.handles or [], job.platforms or [])
        for err in parse_errors:
            logs.append(f"> input_error: {err}")

        job.logs = logs
        await db.commit()

        saved_leads = []
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            job.stage = "scrape"
            job.stage_label = f"Scraping {len(targets)} targets across specified platforms"
            job.stage_index = 2
            await db.commit()

            for target in targets:
                plat = target["platform"]
                handle = target["handle"]
                lead_data = None

                if plat == "github":
                    lead_data = await scrape_github_profile(handle, client)
                elif plat == "linktree":
                    lead_data = await scrape_linktree_profile(handle, client)
                elif plat == "instagram":
                    lead_data = await scrape_instagram_profile(handle, client, apify_token=apify_token)
                elif plat == "linkedin":
                    lead_data = await scrape_linkedin_profile(handle, client, cookie=linkedin_cookie)
                elif plat == "tiktok":
                    lead_data = await scrape_tiktok_profile(handle, client)
                elif plat == "youtube":
                    lead_data = await scrape_youtube_profile(handle, client)
                else:
                    lead_data = {"error": f"platform_{plat}_not_implemented"}

                # Inspect result: ONLY create ScoutLead if real data was extracted without error
                if lead_data and "error" not in lead_data:
                    # Optional Website Enrichment pass
                    website = lead_data.get("website")
                    if job.enrich_emails and website and not lead_data.get("email"):
                        enrich_res = await enrich_from_website(website, client)
                        en_emails = enrich_res.get("emails", [])
                        en_phones = enrich_res.get("phones", [])
                        if en_emails:
                            lead_data["email"] = en_emails[0]
                            lead_data["email_source"] = "website_contact_page"
                        if en_phones and not lead_data.get("phone"):
                            lead_data["phone"] = en_phones[0]
                            lead_data["phone_source"] = "website_contact_page"

                    score = compute_lead_score(
                        lead_data.get("email"),
                        lead_data.get("phone"),
                        lead_data.get("website"),
                        lead_data.get("bio"),
                        lead_data.get("followers")
                    )

                    lead = ScoutLead(
                        job_id=job.id,
                        org_id=job.org_id,
                        platform=plat,
                        handle=handle if handle.startswith("@") else f"@{handle}",
                        name=lead_data.get("name") or handle,
                        email=lead_data.get("email"),
                        phone=lead_data.get("phone"),
                        website=lead_data.get("website"),
                        bio=lead_data.get("bio"),
                        followers=lead_data.get("followers") or 0,
                        lead_score=score,
                        profile_url=target.get("profile_url") or lead_data.get("profile_url"),
                        sources={
                            "email_source": lead_data.get("email_source"),
                            "phone_source": lead_data.get("phone_source"),
                            "confidence": 90 if lead_data.get("email") else 50,
                        },
                    )
                    db.add(lead)
                    saved_leads.append(lead)

                    email_info = f"email: {lead.email}" if lead.email else "no email"
                    logs.append(f"> {plat}:{handle} · verified · {email_info} · score: {score}")
                else:
                    err_msg = lead_data.get("error") if lead_data else "unknown_error"
                    logs.append(f"> {plat}:{handle} · error: {err_msg}")

            # 3. Stage: Enrich
            job.stage = "enrich"
            job.stage_label = f"Enrichment pass completed ({len(saved_leads)} verified leads)"
            job.stage_index = 3
            job.logs = logs
            await db.commit()

            # 4. Stage: Complete
            job.status = "succeeded"
            job.stage = "complete"
            job.stage_label = f"Scout job complete · {len(saved_leads)} leads indexed"
            job.stage_index = 4
            job.leads_count = len(saved_leads)
            job.elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append(f"> job completed in {job.elapsed_ms / 1000:.1f}s · {len(saved_leads)} leads persisted")
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)

            await db.commit()
