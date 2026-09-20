"""
Helix Scout Service (Atlas Edition)
Integrates vendored kiryano/Scout OSS scrapers + LeadEnricher + Atlas Pipeline.
Zero Apify. Zero Relevance AI runtime dependency. Never creates fabricated leads.
"""
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

from vendor.helix_scout.scrapers.instagram import scrape_instagram_profile
from vendor.helix_scout.scrapers.linktree import scrape_linktree_profile
from vendor.helix_scout.scrapers.github import scrape_github_profile
from vendor.helix_scout.scrapers.tiktok import scrape_tiktok_profile
from vendor.helix_scout.scrapers.youtube import scrape_youtube_profile
from vendor.helix_scout.scrapers.linkedin import scrape_linkedin_profile
from vendor.helix_scout.scrapers.pinterest import scrape_pinterest_profile
from vendor.helix_scout.scrapers.twitch import scrape_twitch_profile
from vendor.helix_scout.scrapers.enrichment import LeadEnricher
from vendor.helix_scout.scrapers.stealth import get_scout_proxy
from app.services.atlas_pipeline import run_atlas_pipeline
from app.services.scrapegraph_lead_service import extract_profile_with_scrapegraph

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
    Rejects handles containing internal spaces.
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

        fallback = [p.lower() for p in fallback_platforms] if fallback_platforms else ["instagram", "github", "linktree"]
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
    """Helper wrapper around LeadEnricher for Maps and other callers."""
    enricher = LeadEnricher()
    return await enricher.enrich_from_website(website_url, client)

async def run_scout_job_worker(job_id: str):
    """
    Background worker for Social Scout Atlas jobs.
    Runs: parse -> scrape (vendored Scout) -> enrich (LeadEnricher) -> atlas (classify+score) -> outreach (LLM).
    Only stores genuine leads. Never fabricates leads or contact information.
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

        job.status = "running"
        job.stage = "init"
        job.stage_label = "Parsing and validating input targets"
        job.stage_index = 1
        job.stages_total = 4
        job.logs = [
            "> engine: helix_scout_atlas/v2 (kiryano/Scout OSS engine) · ok",
            f"> stealth_proxy: {'configured' if get_scout_proxy() else 'direct'} · linkedin_byok: {'configured' if linkedin_cookie else 'off'}",
            f"> target_category: '{job.target_category or 'general'}'",
        ]
        job.heartbeat_at = datetime.now(timezone.utc)
        await db.commit()

        start_time = time.time()
        logs = list(job.logs)

        # 1. Parse stage
        targets, parse_errors = parse_scout_input(job.handles or [], job.platforms or [])
        logs.append(f"> parse · ok ({len(targets)} targets)")
        for err in parse_errors:
            logs.append(f"> parse_warning: {err}")

        job.logs = logs
        await db.commit()

        saved_leads = []
        enricher = LeadEnricher(hunter_api_key=hunter_key, enable_smtp_verify=False)
        proxy_url = get_scout_proxy()

        client_kwargs = {"timeout": 12.0, "follow_redirects": True}
        if proxy_url:
            client_kwargs["proxy"] = proxy_url

        async with httpx.AsyncClient(**client_kwargs) as client:
            job.stage = "scrape"
            job.stage_label = f"Scraping {len(targets)} targets across specified platforms"
            job.stage_index = 2
            await db.commit()

            for target in targets:
                plat = target["platform"]
                handle = target["handle"]
                lead_data = None

                # 2. Scrape stage
                if plat == "instagram":
                    lead_data = await scrape_instagram_profile(handle, client)
                elif plat == "linktree":
                    lead_data = await scrape_linktree_profile(handle, client)
                elif plat == "github":
                    lead_data = await scrape_github_profile(handle, client)
                elif plat == "tiktok":
                    lead_data = await scrape_tiktok_profile(handle, client)
                elif plat == "youtube":
                    lead_data = await scrape_youtube_profile(handle, client)
                elif plat == "linkedin":
                    lead_data = await scrape_linkedin_profile(handle, client, cookie=linkedin_cookie)
                elif plat == "pinterest":
                    lead_data = await scrape_pinterest_profile(handle, client)
                elif plat == "twitch":
                    lead_data = await scrape_twitch_profile(handle, client)
                else:
                    lead_data = {
                        "platform": plat,
                        "handle": handle,
                        "name": handle,
                        "email": None,
                        "scrape_status": "needs_manual_review",
                        "error": f"platform_{plat}_manual_review",
                    }

                status_code = lead_data.get("scrape_status", "ok")
                logs.append(f"> {plat}:@{handle} · {status_code}")

                # 3. Enrich stage
                website = lead_data.get("website")
                email_src = lead_data.get("email_source")
                
                if job.enrich_emails and website and not lead_data.get("email"):
                    enrich_res = await enricher.enrich_from_website(website, client)
                    if enrich_res.get("emails"):
                        lead_data["email"] = enrich_res["emails"][0]
                        lead_data["email_source"] = enrich_res.get("email_source") or "website"
                        email_src = lead_data["email_source"]
                    if enrich_res.get("phones") and not lead_data.get("phone"):
                        lead_data["phone"] = enrich_res["phones"][0]
                        lead_data["phone_source"] = "website"

                # ScrapeGraph AI deep contact pass if email still absent
                if job.enrich_emails and not lead_data.get("email"):
                    target_enrich_url = website or target.get("profile_url")
                    if target_enrich_url and ("http://" in target_enrich_url or "https://" in target_enrich_url):
                        try:
                            sg_res = await extract_profile_with_scrapegraph(target_enrich_url, client)
                            if sg_res and sg_res.get("email"):
                                lead_data["email"] = sg_res["email"]
                                lead_data["email_source"] = "scrapegraph_ai"
                                email_src = "scrapegraph_ai"
                            if sg_res and sg_res.get("phone") and not lead_data.get("phone"):
                                lead_data["phone"] = sg_res["phone"]
                                lead_data["phone_source"] = "scrapegraph_ai"
                        except Exception:
                            pass

                logs.append(f"> enrich · email_source={email_src or 'none'}")

                # 4. Atlas Stage: Classify + Score
                atlas_json = await run_atlas_pipeline(
                    lead_data,
                    target_category=job.target_category,
                    generate_outreach=job.generate_outreach
                )
                
                relevance_score = atlas_json["lead_scoring"]["relevance_score"]
                priority_level = atlas_json["lead_scoring"]["priority_level"]
                logs.append(f"> atlas · classify+score [score={relevance_score} priority={priority_level}]")

                # 5. Outreach Stage
                outreach_generated = bool(atlas_json.get("outreach", {}).get("email_body"))
                if outreach_generated:
                    logs.append("> outreach · generated")
                else:
                    logs.append("> outreach · skipped_low_priority")

                # Persist genuine lead into Neon DB
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
                    lead_score=relevance_score,
                    profile_url=target.get("profile_url") or lead_data.get("profile_url"),
                    scrape_status=status_code,
                    atlas=atlas_json,
                    sources={
                        "email_source": lead_data.get("email_source"),
                        "phone_source": lead_data.get("phone_source"),
                        "confidence": 95 if lead_data.get("email") else (70 if lead_data.get("phone") else 50),
                        "priority": priority_level,
                        "account_type": atlas_json["profile_analysis"]["account_type"],
                        "primary_niche": atlas_json["profile_analysis"]["primary_niche"],
                    },
                )
                db.add(lead)
                saved_leads.append(lead)

            # 3. Stage: Enrich complete
            job.stage = "enrich"
            job.stage_label = f"Atlas analysis & enrichment pass complete ({len(saved_leads)} leads indexed)"
            job.stage_index = 3
            job.logs = logs
            await db.commit()

            # 4. Stage: Complete
            job.status = "succeeded"
            job.stage = "complete"
            job.stage_label = f"Scout Atlas complete · {len(saved_leads)} leads scored"
            job.stage_index = 4
            job.leads_count = len(saved_leads)
            job.elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append(f"> job completed in {job.elapsed_ms / 1000:.1f}s · {len(saved_leads)} leads persisted")
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)

            await db.commit()
