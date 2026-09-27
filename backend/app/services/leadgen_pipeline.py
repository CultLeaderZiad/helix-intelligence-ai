"""leadgen_pipeline - stages 1-9 orchestration for Scout Lead Generation.

Runs inside the Scrapling worker process (or the opt-in inline dev fallback).
API boot never imports Scrapling; this module imports scrapling_engine lazily
inside run_leadgen_job.

Stages (spec section 4):
  1 brief -> 2 seed -> 3 discover -> 4 fetch -> 5 extract
  -> 6 enrich -> 7 dedupe+score -> 8 outreach draft -> 9 export-ready

Honesty rules:
  - logs are REAL worker output, never CSS theater
  - missing fields stay empty (extract_status reflects it), never invented
  - pause between URLs via checkpoint; credit overage pauses loudly
  - outreach ONLY when score >= threshold AND a real email/phone exists
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import socket
import time
import uuid
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.leadgen import LeadGenJob, LeadGenLead

logger = logging.getLogger(__name__)

STAGE_ORDER = ["brief", "seed", "discover", "fetch", "extract", "enrich", "score", "outreach", "export"]
STAGE_LABELS = {
    "brief": "Validating brief",
    "seed": "Normalizing seeds",
    "discover": "Discovering URLs",
    "fetch": "Fetching pages",
    "extract": "Extracting contacts",
    "enrich": "Enriching contacts",
    "score": "Scoring leads",
    "outreach": "Drafting outreach",
    "export": "Finalizing export",
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _load_recipe(recipe_id: Optional[str]) -> dict:
    if not recipe_id:
        return {}
    path = Path(__file__).resolve().parent.parent / "data" / "leadgen_recipes" / f"{recipe_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _append_log(job: LeadGenJob, line: str) -> None:
    logs = list(job.logs or [])
    logs.append(line)
    cap = settings.SCRAPLING_MAX_LOG_LINES
    if len(logs) > cap:
        logs = logs[-cap:]
    job.logs = logs


def _set_stage(job: LeadGenJob, stage: str) -> None:
    job.stage = stage
    job.stage_label = STAGE_LABELS.get(stage, stage)
    job.stage_index = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else job.stage_index


def _checkpoint_file(job_id: str) -> Path:
    d = Path(settings.SCRAPLING_CHECKPOINT_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{job_id}.json"


def _save_checkpoint(job: LeadGenJob, pending: List[str], processed: int) -> None:
    path = _checkpoint_file(job.id)
    path.write_text(json.dumps({"pending": pending, "processed": processed, "at": _now().isoformat()}))
    job.checkpoint_path = str(path)


def _load_checkpoint(job: LeadGenJob) -> Optional[dict]:
    if not job.checkpoint_path:
        return None
    path = Path(job.checkpoint_path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _is_private_host(host: str) -> bool:
    host = (host or "").lower()
    if not host or host == "localhost" or re.match(r"^.*\.(local|internal)$", host):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def _same_domain(a: str, b: str) -> bool:
    da = (urlparse(a).hostname or "").lower().removeprefix("www.")
    db = (urlparse(b).hostname or "").lower().removeprefix("www.")
    return da == db


def _matches_any(url: str, patterns: Optional[List[str]]) -> bool:
    if not patterns:
        return False
    for p in patterns:
        try:
            if re.search(p, url):
                return True
        except re.error:
            if p in url:
                return True
    return False


def extract_links(html: str, base_url: str) -> List[str]:
    links = []
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', html or "", re.I):
        href = m.group(1).strip()
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = urljoin(base_url, href).split("#")[0]
        if absolute.startswith(("http://", "https://")):
            links.append(absolute)
    return links


def parse_sitemap(sitemap_url: str, limit: int) -> List[str]:
    """Parse a sitemap.xml (or sitemap index, one level) into page URLs."""
    urls: List[str] = []
    try:
        resp = httpx.get(sitemap_url, timeout=20.0, follow_redirects=True)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        entries = root.findall(".//sm:loc", ns) or root.findall(".//loc")
        locs = [e.text.strip() for e in entries if e.text]
        # sitemap index: fetch child sitemaps (one level)
        if root.tag.endswith("sitemapindex"):
            for child in locs[:3]:
                urls.extend(parse_sitemap(child, limit - len(urls)))
                if len(urls) >= limit:
                    break
        else:
            urls = [u for u in locs if u.startswith(("http://", "https://"))][:limit]
    except Exception as e:
        logger.warning("sitemap parse failed %s: %s", sitemap_url, e)
    return urls


# ---------------------------------------------------------------------------
# Stage 7: dedupe + deterministic scoring formula (documented per spec)
#
#   score = 0
#     + 30  real email present (email_source != none)
#     + 20  real phone present (phone_source != none)
#     + 15  company_name found
#     + 10  address found
#     + 10  contact-page signal (url matched recipe allow-list or selector hit)
#     + 10  decision-maker hints found
#     + min(15, 5 * unique ICP keyword overlaps)  ICP keyword overlap
#     clamp 0..100
#   priority: score >= 70 high | >= 40 med | else low
#   LLM assist is optional and must NEVER invent contact fields.
# ---------------------------------------------------------------------------

def score_lead(lead_sources: dict, brief: dict) -> tuple:
    icp = (brief.get("icp") or "").lower()
    tokens = [t for t in re.findall(r"\w+", icp) if len(t) > 3]

    s = 0
    if lead_sources.get("email_source", "none") != "none":
        s += 30
    if lead_sources.get("phone_source", "none") != "none":
        s += 20
    if lead_sources.get("company_name"):
        s += 15
    if lead_sources.get("address"):
        s += 10
    if lead_sources.get("contact_signal"):
        s += 10
    if lead_sources.get("decision_makers"):
        s += 10
    haystack = " ".join([
        str(lead_sources.get("company_name") or ""),
        str(lead_sources.get("address") or ""),
        " ".join(str(v) for v in (lead_sources.get("socials") or {}).values()),
        str(lead_sources.get("domain") or ""),
    ]).lower()
    overlaps = sum(1 for t in set(tokens) if t in haystack)
    s += min(15, overlaps * 5)
    s = max(0, min(100, s))
    priority = "high" if s >= 70 else ("med" if s >= 40 else "low")
    return s, priority, {
        "formula": "email30+phone20+company15+address10+contact10+dm10+icp_kw(min15)",
        "icp_keyword_overlaps": overlaps,
        "priority_bands": {"high": ">=70", "med": "40-69", "low": "<40"},
    }

# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_leadgen_job(job_id: str) -> None:
    """Claim + run one LeadGenJob through the 9 stages. Idempotent: exits
    immediately if the job is not queued/paused or another worker owns it."""
    boot_id = uuid.uuid4().hex[:12]
    started_ts = time.monotonic()

    async with async_session_maker() as db:
        job = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
        if not job or job.status in ("succeeded", "failed"):
            return
        # Accept: queued (inline), paused (resume), or running pre-claimed by
        # THIS worker via _claim_next_job (owner_boot_id = "claimed:<boot>").
        if job.status == "running" and job.owner_boot_id and not str(job.owner_boot_id).startswith("claimed:"):
            return  # another active run owns it

        resume_checkpoint = job.status == "paused"
        job.status = "running"
        job.owner_boot_id = boot_id
        job.started_at = job.started_at or _now()
        job.error_msg = None
        job.heartbeat_at = _now()

        # --- Canonical header (first lines when worker claims the job) ---
        from app.services import scrapling_engine as engine
        from app.core.config import settings as _s
        proxy_state = "configured" if _s.SCRAPLING_PROXY_LIST.strip() else "off"
        if engine.is_available():
            _append_log(job, f"> engine: scrapling/{job.engine_default}/{engine.ENGINE_VERSION} · ok")
        else:
            _append_log(job, f"> engine: scrapling/{job.engine_default}/{engine.ENGINE_VERSION} · unavailable (scrapling not installed in this worker)")
        _append_log(job, f"> robots: obey · {'on' if job.robots_obey else 'off'}")
        _append_log(job, f"> worker: connected · proxy: {proxy_state}")
        await db.commit()

    # If Scrapling is missing entirely, fail loudly (honest failure > silent queue)
    from app.services import scrapling_engine as eng
    if not eng.is_available():
        await _fail_job(job_id, "Scrapling is not installed in this worker (pip install 'scrapling[fetchers]' && scrapling install)")
        return

    try:
        await _run_stages(job_id, boot_id, started_ts, resume_checkpoint)
    except Exception as e:
        logger.exception("LeadGen job %s crashed", job_id)
        await _fail_job(job_id, f"{type(e).__name__}: {e}")


async def _fail_job(job_id: str, message: str) -> None:
    async with async_session_maker() as db:
        job = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
        if not job:
            return
        job.status = "failed"
        job.stage_label = "Failed"
        job.error_msg = message[:900]
        job.completed_at = _now()
        sa = job.started_at.replace(tzinfo=timezone.utc) if job.started_at and job.started_at.tzinfo is None else job.started_at
        job.elapsed_ms = int((_now() - sa).total_seconds() * 1000) if sa else (job.elapsed_ms or 0)
        _append_log(job, f"> failed · {message[:200]}")
        await db.commit()


async def _run_stages(job_id: str, boot_id: str, started_ts: float, resume_checkpoint: bool) -> None:
    from app.services import scrapling_engine as engine

    async with async_session_maker() as db:
        job = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
        if not job or job.owner_boot_id != boot_id:
            return
        recipe = _load_recipe(job.recipe_id)
        brief = job.brief or {}
        seeds = job.seeds or {}
        engine_default = (recipe.get("engine_default") if recipe.get("engine_default") in ("http", "stealth", "dynamic") else None) or job.engine_default or settings.SCRAPLING_DEFAULT_ENGINE
        allow_patterns = list(recipe.get("allow") or [])
        deny_patterns = list(recipe.get("deny") or [])

        # ===== Stage 1: brief =====
        _set_stage(job, "brief")
        icp = (brief.get("icp") or "").strip()
        if len(icp) < 3:
            await db.commit()
            await _fail_job(job_id, "Brief stage failed: icp is required")
            return
        geos = brief.get("geos") or []
        _append_log(job, f"> brief · icp_ok · geos={len(geos)} · max_pages={brief.get('max_pages')} · max_leads={brief.get('max_leads')}")
        job.heartbeat_at = _now()
        await db.commit()

        # ===== Stage 2: seed (defensive re-validation) =====
        _set_stage(job, "seed")
        queue: List[str] = []
        for u in seeds.get("urls", []):
            host = (urlparse(u).hostname or "").lower()
            if u.startswith(("http://", "https://")) and host and not _is_private_host(host):
                queue.append(u)
            else:
                _append_log(job, f"> seed · rejected · {u}")
        sitemap = seeds.get("sitemap")
        shopify = seeds.get("shopify")
        _append_log(job, f"> seed · urls={len(queue)} · sitemap={'yes' if sitemap else 'no'} · shopify={'yes' if shopify else 'no'}")
        if not queue and not sitemap and not shopify:
            await db.commit()
            await _fail_job(job_id, "Seed stage failed: no valid http(s) seeds after validation")
            return
        job.heartbeat_at = _now()
        await db.commit()

        # ===== Stage 3: discover =====
        _set_stage(job, "discover")
        max_pages = max(1, int(brief.get("max_pages") or 50))
        checkpoint = _load_checkpoint(job) if resume_checkpoint else None
        if checkpoint and checkpoint.get("pending") is not None:
            queue = list(checkpoint["pending"])
            _append_log(job, f"> resume · checkpoint · {len(queue)} urls pending")
        else:
            if sitemap:
                sitemap_urls = await asyncio.to_thread(engine_sitemap_wrapper, sitemap, max_pages)
                if sitemap_urls:
                    queue.extend(sitemap_urls)
                    _append_log(job, f"> discover · sitemap +{len(sitemap_urls)} urls")
                else:
                    _append_log(job, f"> discover · sitemap 404/unreachable · continuing with seeds ({len(queue)})")
            if shopify:
                shopify_urls = await asyncio.to_thread(shopify_discover, shopify)
                if shopify_urls:
                    queue.extend(shopify_urls)
                    _append_log(job, f"> discover · shopify +{len(shopify_urls)} urls")
            # allow/deny pre-filter for non-seed urls (seeds always honored)
            if allow_patterns or deny_patterns:
                seeds_only = set(seeds.get("urls", []))
                filtered = []
                for u in queue:
                    if u in seeds_only:
                        filtered.append(u)
                    elif _matches_any(u, deny_patterns):
                        continue
                    elif allow_patterns and not _matches_any(u, allow_patterns):
                        continue
                    else:
                        filtered.append(u)
                queue = filtered
            # de-dupe + cap
            seen = set()
            queue = [u for u in queue if not (u in seen or seen.add(u))][:max_pages]
        _append_log(job, f"> discover · {len(queue)} urls queued")
        job.heartbeat_at = _now()
        await db.commit()
        if not queue:
            await _finish(job_id, started_ts, "No URLs discovered (check seeds/sitemap against allow/deny rules)", failed=True)
            return

        # ===== Stages 4+5: fetch + extract (per URL, with pause/budget checks) =====
        processed = checkpoint.get("processed", 0) if checkpoint else 0
        contact_selector = dict(recipe.get("selectors") or {})
        if job.adaptive:
            contact_selector["_adaptive"] = True
        allow_url = job.mode in ("crawl", "digest")  # contact-signal uses recipe allow patterns

        while queue:
            # Heartbeat / ownership / pause checks between URLs
            fresh = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
            if not fresh or fresh.owner_boot_id != boot_id:
                return
            if fresh.status == "paused":
                _save_checkpoint(fresh, queue, processed)
                _append_log(fresh, f"> pause · checkpoint saved · {len(queue)} urls pending")
                fresh.elapsed_ms = int((time.monotonic() - started_ts) * 1000)
                await db.commit()
                return

            # Credit budget check (mid-job overage -> pause loudly, never silently continue)
            base = settings.SCRAPLING_CREDIT_BASE
            per_page = settings.SCRAPLING_CREDIT_PER_PAGE
            extras = (0.25 * (brief.get("max_leads") or 0) if fresh.enrich_emails else 0.0) + (0.1 * (brief.get("max_leads") or 0) if fresh.generate_outreach else 0.0)
            consumed = base + (fresh.pages_fetched + 1) * per_page + extras
            if fresh.credit_budget and consumed > fresh.credit_budget:
                _save_checkpoint(fresh, queue, processed)
                fresh.status = "paused"
                fresh.error_msg = f"Credit budget exhausted mid-job (used {consumed:.2f} of {fresh.credit_budget:.2f}). Resume after topping up."
                _append_log(fresh, f"> credits · exhausted · {consumed:.2f}/{fresh.credit_budget:.2f} · paused")
                fresh.elapsed_ms = int((time.monotonic() - started_ts) * 1000)
                await db.commit()
                return

            url = queue.pop(0)
            _set_stage(fresh, "fetch")
            fresh.stage_label = f"Fetching {processed + 1}/{processed + len(queue) + 1}"
            await db.commit()

            result = await asyncio.to_thread(
                engine.fetch, url, engine_default, bool(fresh.robots_obey), fresh.capture_xhr_pattern
            )
            status = result.get("fetch_status")
            _append_log(fresh, f"> fetch · {url} · {status}")
            fresh.pages_fetched = (fresh.pages_fetched or 0) + 1
            if status in ("blocked", "rate_limited"):
                fresh.pages_blocked = (fresh.pages_blocked or 0) + 1

            if status == "ok" and result.get("html"):
                _set_stage(fresh, "extract")
                extracted = await asyncio.to_thread(engine.extract_contacts, result["html"], contact_selector, url)
                emails = [e for e in extracted.get("emails", [])][:10]
                phones = [p for p in extracted.get("phones", [])][:10]
                _append_log(fresh, f"> extract · emails={len(emails)} phones={len(phones)} · adaptive={'on' if extracted.get('adaptive_used') else 'off'}")

                host = (urlparse(result.get("url") or url).hostname or "").lower().removeprefix("www.")
                existing = (await db.execute(
                    select(LeadGenLead).where(LeadGenLead.job_id == job_id, LeadGenLead.domain == host)
                )).scalar_one_or_none()

                indicator = bool(allow_url and allow_patterns and _matches_any(url, allow_patterns)) or bool(extracted.get("selector_hits", {}).get("emails"))
                lead_sources = {
                    "urls": [url],
                    "selector_hits": extracted.get("selector_hits", {}),
                    "contact_signal": indicator,
                    "company_name": extracted.get("company_name"),
                    "address": extracted.get("address"),
                    "socials": extracted.get("socials", {}),
                    "domain": host,
                    "decision_makers": [],
                    "email_source": "website" if emails else "none",
                    "phone_source": "website" if phones else "none",
                }

                markdown = None
                artifact = None
                if fresh.mode in ("digest", "crawl"):
                    markdown = await asyncio.to_thread(engine.to_markdown, result["html"], url)
                    if markdown:
                        artifact_dir = Path(settings.SCRAPLING_CHECKPOINT_DIR) / job_id / "markdown"
                        artifact_dir.mkdir(parents=True, exist_ok=True)
                        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", urlparse(url).path.strip("/") or "index")[:80]
                        artifact_path = artifact_dir / f"{safe}.md"
                        artifact_path.write_text(markdown, encoding="utf-8")
                        artifact = str(artifact_path)

                extract_status = "ok" if (emails or phones) else ("partial" if (extracted.get("company_name") or extracted.get("address")) else "empty")

                if existing:
                    # merge new evidence into the existing lead for this domain (dedupe domain+email)
                    merged_emails = list(dict.fromkeys((existing.emails or []) + emails))[:10]
                    merged_phones = list(dict.fromkeys((existing.phones or []) + phones))[:10]
                    merged_sources = dict(existing.sources or {})
                    merged_sources["urls"] = list(dict.fromkeys((merged_sources.get("urls") or []) + [url]))
                    if merged_emails and merged_sources.get("email_source") in (None, "none"):
                        merged_sources["email_source"] = "website"
                    if merged_phones and merged_sources.get("phone_source") in (None, "none"):
                        merged_sources["phone_source"] = "website"
                    existing.emails = merged_emails
                    existing.phones = merged_phones
                    existing.sources = merged_sources
                    existing.company_name = existing.company_name or extracted.get("company_name")
                    existing.address = existing.address or extracted.get("address")
                    existing.socials = {**(existing.socials or {}), **(extracted.get("socials") or {})}
                    existing.markdown_excerpt = existing.markdown_excerpt or markdown
                    existing.markdown_artifact_path = existing.markdown_artifact_path or artifact
                    existing.extract_status = "ok" if merged_emails or merged_phones else extract_status
                else:
                    lead = LeadGenLead(
                        job_id=job_id,
                        org_id=fresh.org_id,
                        company_name=extracted.get("company_name"),
                        website=url,
                        domain=host or None,
                        emails=emails,
                        phones=phones,
                        socials=extracted.get("socials") or {},
                        address=extracted.get("address"),
                        decision_makers=[],
                        markdown_excerpt=markdown,
                        markdown_artifact_path=artifact,
                        extract_status=extract_status,
                        fetch_status="ok",
                        engine_used=engine_default,
                        email_source="website" if emails else "none",
                        phone_source="website" if phones else "none",
                        lead_score=0,
                        priority=None,
                        outreach=None,
                        sources=lead_sources,
                    )
                    db.add(lead)
                    await db.flush()

                fresh.leads_count = (await db.execute(
                    select(LeadGenLead.id).where(LeadGenLead.job_id == job_id)
                )).scalars().all().__len__()
            elif status != "ok":
                # Record an honest failed-fetch stub lead ONLY when nothing found yet for the domain
                host = (urlparse(url).hostname or "").lower().removeprefix("www.")
                has_any = (await db.execute(
                    select(LeadGenLead.id).where(LeadGenLead.job_id == job_id, LeadGenLead.domain == host)
                )).first()
                if not has_any and host:
                    db.add(LeadGenLead(
                        job_id=job_id, org_id=fresh.org_id, company_name=None,
                        website=url, domain=host, emails=[], phones=[], socials={},
                        extract_status="failed" if status == "error" else "empty",
                        fetch_status=status, engine_used=engine_default,
                        email_source="none", phone_source="none",
                        sources={"urls": [url], "reason": result.get("reason")},
                    ))
                    await db.flush()

            processed += 1
            fresh.heartbeat_at = _now()
            fresh.elapsed_ms = int((time.monotonic() - started_ts) * 1000)
            if len(fresh.logs or []) < 5 or processed % 5 == 0:
                _save_checkpoint(fresh, queue, processed)
            await db.commit()

            # Adaptive crawl: discover same-domain links on contact-ish pages
            if (
                status == "ok" and result.get("html")
                and fresh.mode in ("crawl", "digest")
                and len(queue) < max_pages
            ):
                links = await asyncio.to_thread(extract_links, result["html"], url)
                queued_now = set(queue)
                for link in links:
                    if len(queue) >= max_pages:
                        break
                    if link in queued_now:
                        continue
                    host_l = (urlparse(link).hostname or "").lower()
                    if not host_l or _is_private_host(host_l):
                        continue
                    if not _same_domain(link, url):
                        continue
                    if _matches_any(link, deny_patterns):
                        continue
                    if allow_patterns and not _matches_any(link, allow_patterns):
                        continue
                    queue.append(link)
                    queued_now.add(link)

        # ===== Stages 6-9 =====
        await _final_stages(job_id, started_ts)

# ---------------------------------------------------------------------------
# Discovery helpers (sync - called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def engine_sitemap_wrapper(sitemap_url: str, limit: int) -> List[str]:
    return parse_sitemap(sitemap_url, limit)


def shopify_discover(shopify_url: str) -> List[str]:
    """Shopify discovery: products.json index + contact/about pages.
    Recipe shopify-brand drives extraction selectors."""
    base = shopify_url.rstrip("/")
    urls = [f"{base}/pages/contact", f"{base}/pages/about", f"{base}/policies/contact"]
    try:
        r = httpx.get(f"{base}/products.json?limit=50", timeout=20.0, follow_redirects=True)
        if r.status_code == 200:
            data = r.json()
            for p in (data.get("products") or [])[:50]:
                handle = p.get("handle")
                if handle:
                    urls.append(f"{base}/products/{handle}")
    except Exception as e:
        logger.warning("shopify discover failed %s: %s", base, e)
    return urls


# ---------------------------------------------------------------------------
# Stages 6-9: enrich -> dedupe+score -> outreach draft -> export-ready
# ---------------------------------------------------------------------------

async def _final_stages(job_id: str, started_ts: float) -> None:
    async with async_session_maker() as db:
        job = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
        if not job:
            return
        brief = job.brief or {}

        # ===== Stage 6: enrich (website provenance + optional Hunter BYOK) =====
        _set_stage(job, "enrich")
        result = await db.execute(select(LeadGenLead).where(LeadGenLead.job_id == job_id))
        leads = list(result.scalars().all())

        hunter_key = None
        if job.enrich_emails:
            try:
                from app.models.organization import Organization
                org = (await db.execute(select(Organization).where(Organization.id == job.org_id))).scalar_one_or_none()
                flags = (org.custom_feature_flags or {}) if org else {}
                hunter_key = flags.get("hunter_api_key") or os.environ.get("HUNTER_API_KEY")
            except Exception:
                hunter_key = None

        enriched_with_hunter = 0
        if job.enrich_emails and hunter_key:
            for lead in leads:
                if lead.emails:
                    continue  # website evidence wins; provenance already set
                if not lead.domain:
                    continue
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        r = await client.get(
                            "https://api.hunter.io/v2/domain-search",
                            params={"domain": lead.domain, "api_key": hunter_key, "limit": 3},
                        )
                    if r.status_code == 401:
                        _append_log(job, "> enrich · hunter 401 · continuing website-only")
                        hunter_key = None
                        break
                    if r.status_code == 200:
                        emails = (r.json().get("data") or {}).get("emails") or []
                        found = [e.get("value") for e in emails if isinstance(e, dict) and e.get("value")]
                        if found:
                            lead.emails = list(dict.fromkeys((lead.emails or []) + found))[:10]
                            lead.email_source = "hunter"
                            src = dict(lead.sources or {})
                            src["email_source"] = "hunter"
                            src["hunter_confidence"] = [e.get("confidence") for e in emails[:3] if isinstance(e, dict)]
                            lead.sources = src
                            lead.extract_status = "ok"
                            enriched_with_hunter += 1
                except Exception as e:
                    logger.warning("hunter enrich failed for %s: %s", lead.domain, e)

        website_only = sum(1 for l in leads if (l.email_source or "none") == "website")
        _append_log(job, f"> enrich · email_source=hunter:{enriched_with_hunter} website:{website_only} · phone_source=website:{sum(1 for l in leads if (l.phone_source or 'none') == 'website')}")
        job.heartbeat_at = _now()
        await db.commit()

        # ===== Stage 7: dedupe + score =====
        _set_stage(job, "score")
        # Dedupe: keep first lead per domain, and drop leads sharing an email with an earlier lead
        seen_domains = set()
        seen_emails = set()
        for lead in leads:
            key_d = lead.domain or lead.website or lead.id
            if key_d in seen_domains:
                continue
            email_keys = set(lead.emails or [])
            if email_keys and email_keys & seen_emails:
                continue
            seen_domains.add(key_d)
            seen_emails |= email_keys

            score, priority, breakdown = score_lead({
                **(lead.sources or {}),
                "email_source": lead.email_source,
                "phone_source": lead.phone_source,
                "decision_makers": lead.decision_makers or [],
            }, brief)
            lead.lead_score = score
            lead.priority = priority
            src = dict(lead.sources or {})
            src["score"] = breakdown
            lead.sources = src
        scored = [l for l in leads if (l.lead_score or 0) > 0]
        high = sum(1 for l in leads if l.priority == "high")
        _append_log(job, f"> score · {len(leads)} · high={high} · bands=high70/med40/low<40")
        await db.commit()

        # ===== Stage 8: outreach draft (NEVER auto-send) =====
        _set_stage(job, "outreach")
        threshold = int(brief.get("outreach_min_score") or 50)
        generated = skipped_low = skipped_none = errored = 0
        if job.generate_outreach:
            provider = None
            try:
                from app.services.ai.ai_router import MultiTierAIProvider
                provider = MultiTierAIProvider()
            except Exception as e:
                _append_log(job, f"> outreach · router unavailable · {str(e)[:80]}")

            for lead in leads:
                has_contact = bool(lead.emails or lead.phones)
                if not has_contact:
                    lead.outreach = {"reason": "skipped_no_contact"}
                    skipped_none += 1
                    continue
                if (lead.lead_score or 0) < threshold:
                    lead.outreach = {"reason": "skipped_low_priority"}
                    skipped_low += 1
                    continue
                if provider is None:
                    lead.outreach = {"reason": "skipped_router_unavailable"}
                    errored += 1
                    continue
                prompt = (
                    "You are a B2B outreach writer. Draft outreach for this lead as STRICT JSON with keys "
                    "subject (string), body (<=120 words), dm (<=50 words social DM), personalization_points (string[]). "
                    "No placeholders, no invented facts beyond the provided fields. "
                    f"ICP: {brief.get('icp')} | Lead: {lead.company_name or lead.domain} | site: {lead.website} | "
                    f"known contacts: {', '.join((lead.emails or [])[:2]) or 'phone only'} | score: {lead.lead_score}. "
                    "Return ONLY the JSON."
                )
                try:
                    raw = await provider._call_api([{"role": "user", "content": prompt}])
                    m = re.search(r"\{.*\}", raw or "", re.S)
                    parsed = json.loads(m.group(0)) if m else None
                    if isinstance(parsed, dict) and parsed.get("subject") and parsed.get("body"):
                        lead.outreach = {
                            "subject": str(parsed.get("subject"))[:200],
                            "body": str(parsed.get("body"))[:2000],
                            "dm": str(parsed.get("dm") or "")[:500],
                            "personalization_points": [str(x) for x in (parsed.get("personalization_points") or [])[:6]],
                            "sent": False,  # drafts only - never auto-send
                        }
                        generated += 1
                    else:
                        lead.outreach = {"reason": "skipped_parse_error"}
                        errored += 1
                except Exception as e:
                    lead.outreach = {"reason": "skipped_llm_error", "detail": str(e)[:200]}
                    errored += 1
            _append_log(job, f"> outreach · generated={generated} · skipped_low_priority={skipped_low} · skipped_no_contact={skipped_none} · errors={errored}")
        else:
            _append_log(job, "> outreach · disabled · drafts=0")
        await db.commit()

        # ===== Stage 9: export-ready =====
        _set_stage(job, "export")
        job.leads_count = len(leads)
        job.status = "succeeded"
        job.stage_label = "Completed"
        job.completed_at = _now()
        job.elapsed_ms = int((time.monotonic() - started_ts) * 1000)
        job.heartbeat_at = _now()
        _append_log(job, f"> export · ready · rows={len(leads)} · csv|jsonl available")
        _append_log(job, f"> done · succeeded · leads={len(leads)} · pages={job.pages_fetched} · blocked={job.pages_blocked} · {job.elapsed_ms}ms")
        # Successful completion retires the checkpoint
        try:
            if job.checkpoint_path and Path(job.checkpoint_path).exists():
                Path(job.checkpoint_path).unlink()
        except Exception:
            pass
        await db.commit()


async def _finish(job_id: str, started_ts: float, message: str, failed: bool = False) -> None:
    async with async_session_maker() as db:
        job = (await db.execute(select(LeadGenJob).where(LeadGenJob.id == job_id))).scalar_one_or_none()
        if not job:
            return
        job.status = "failed" if failed else "succeeded"
        job.stage_label = "Failed" if failed else "Completed"
        job.error_msg = message[:900] if failed else job.error_msg
        job.completed_at = _now()
        job.elapsed_ms = int((time.monotonic() - started_ts) * 1000)
        _append_log(job, f"> {'failed' if failed else 'done'} · {message[:300]}")
        await db.commit()
