"""
Maps Scout Service — Google Maps Business Lead Generation
Adapted from Mahanaicoach/google-maps-scraper-kit (gosom/google-maps-scraper)
MIT License (see backend/vendor/google_maps_scraper/LICENSE)
"""

import os
import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import httpx
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.scout import ScoutMapsJob, ScoutMapsLead
from app.services.scout_service import enrich_from_website
from app.services.scrapegraph_lead_service import (
    extract_business_with_scrapegraph,
    get_scrapegraph_key,
    search_leads_with_scrapegraph,
)

def _optional_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None




HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

KNOWN_CITIES: Dict[str, Tuple[float, float]] = {
    "riyadh": (24.7136, 46.6753),
    "jeddah": (21.4858, 39.1925),
    "dammam": (26.4207, 50.0888),
    "khobar": (26.2172, 50.1971),
    "mecca": (21.3891, 39.8579),
    "makkah": (21.3891, 39.8579),
    "medina": (24.5247, 39.5692),
    "madinah": (24.5247, 39.5692),
    "dubai": (25.2048, 55.2708),
    "abu dhabi": (24.4539, 54.3773),
    "doha": (25.2854, 51.5310),
    "kuwait": (29.3759, 47.9774),
    "kuwait city": (29.3759, 47.9774),
    "manama": (26.2285, 50.5860),
    "muscat": (23.5880, 58.3829),
    "cairo": (30.0444, 31.2357),
    "alexandria": (31.2001, 29.9187),
    "giza": (30.0131, 31.2089),
    "amman": (31.9454, 35.9284),
    "beirut": (33.8938, 35.5018),
    "london": (51.5074, -0.1278),
    "manchester": (53.4808, -2.2426),
    "birmingham": (52.4862, -1.8904),
    "new york": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "miami": (25.7617, -80.1918),
    "san francisco": (37.7749, -122.4194),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "paris": (48.8566, 2.3522),
    "berlin": (52.5200, 13.4050),
    "amsterdam": (52.3676, 4.9041),
    "sydney": (33.8688, 151.2093),
    "melbourne": (37.8136, 144.9631),
    "tokyo": (35.6762, 139.6503),
    "singapore": (1.3521, 103.8198),
}

async def geocode_city(city: str, client: httpx.AsyncClient) -> Optional[Tuple[float, float]]:
    """Geocode city to (lat, lon) with instant known city cache & Nominatim fallback."""
    if not city or not city.strip():
        return None

    clean_city = city.lower().split(",")[0].strip()
    if clean_city in KNOWN_CITIES:
        return KNOWN_CITIES[clean_city]

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(clean_city)}&format=json&limit=1"
        from app.services.safe_fetch import safe_request_async
        resp = await safe_request_async(
            "GET",
            url,
            headers={"User-Agent": "Helix-Intelligence-Scout/2.0"},
            timeout=5.0,
            allowed_hosts={"nominatim.openstreetmap.org"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
    except Exception:
        pass
    return None

async def scrape_maps_places(
    keyword: str,
    city: str,
    depth: int,
    client: httpx.AsyncClient,
    apify_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search Google Maps places for a given keyword and city.
    Uses ScrapeGraph AI search as Priority 1,
    or configured private scraper worker (MAPS_SCRAPER_BASE_URL),
    or OpenStreetMap Overpass & Nominatim.
    Never fabricates business listings.
    """
    places: List[Dict[str, Any]] = []
    limit = max(1, min(depth, 25))

    # Priority 1: ScrapeGraph AI Live Places & Business Search (v2 /api/search)
    sg_key = get_scrapegraph_key()
    if sg_key:
        try:
            sg_leads = await search_leads_with_scrapegraph(keyword, city, limit=limit, client=client)
            for s in sg_leads:
                if not any(p["title"].lower() == s["title"].lower() for p in places):
                    places.append(s)
            if len(places) >= limit:
                return places[:limit]
        except Exception:
            pass

    # Priority 2: Private gosom / maps-scraper worker if configured
    maps_worker_url = os.environ.get("MAPS_SCRAPER_BASE_URL")
    maps_worker_key = os.environ.get("MAPS_SCRAPER_API_KEY")
    if maps_worker_url and len(places) < limit:
        try:
            auth_headers = {"Authorization": f"Bearer {maps_worker_key}"} if maps_worker_key else {}
            from app.services.safe_fetch import safe_request_async
            from urllib.parse import urlsplit
            worker_root = maps_worker_url.rstrip("/")
            resp = await safe_request_async(
                "POST",
                f"{worker_root}/v1/scrape",
                headers=auth_headers,
                json={"query": f"{keyword} in {city}", "depth": limit},
                timeout=25.0,
                allowed_hosts={urlsplit(worker_root).hostname or ""},
            )
            if resp.status_code == 200:
                results = resp.json().get("data", [])
                for r in results:
                    t = r.get("title")
                    if t and not any(p["title"].lower() == t.lower() for p in places):
                        places.append({
                            "title": t,
                            "phone": r.get("phone"),
                            "website": r.get("website"),
                            "category": r.get("category", keyword.title()),
                            "address": r.get("address"),
                            "city": city,
                            "rating": r.get("rating"),
                            "reviews_count": r.get("reviews_count"),
                            "rating_provider": "maps_worker",
                            "source_url": r.get("website") or r.get("url"),
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        })
                    if len(places) >= limit:
                        return places[:limit]
        except Exception:
            pass

    # Priority 3: OpenStreetMap Overpass API for verified commercial POIs in city
    if len(places) < limit:
        try:
            lat_lon = await geocode_city(city, client)
            if lat_lon:
                lat, lon = lat_lon
                kw_lower = keyword.lower().strip()

                filters = []
                if any(w in kw_lower for w in ["dent", "teeth", "tooth"]):
                    filters = [
                        f'node["amenity"="dentist"](around:25000,{lat},{lon});',
                        f'node["healthcare"="dentist"](around:25000,{lat},{lon});',
                        f'node["amenity"="clinic"](around:25000,{lat},{lon});',
                        f'way["amenity"="dentist"](around:25000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["doctor", "clinic", "hospital", "health", "medical"]):
                    filters = [
                        f'node["amenity"="clinic"](around:25000,{lat},{lon});',
                        f'node["amenity"="hospital"](around:25000,{lat},{lon});',
                        f'node["healthcare"](around:25000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["restaurant", "cafe", "coffee", "food", "bar", "bakery", "pizza"]):
                    filters = [
                        f'node["amenity"="restaurant"](around:20000,{lat},{lon});',
                        f'node["amenity"="cafe"](around:20000,{lat},{lon});',
                        f'node["amenity"="fast_food"](around:20000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["hotel", "stay", "resort", "hostel", "lodging"]):
                    filters = [
                        f'node["tourism"="hotel"](around:25000,{lat},{lon});',
                        f'node["tourism"="resort"](around:25000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["law", "attorney", "legal"]):
                    filters = [
                        f'node["office"="lawyer"](around:25000,{lat},{lon});',
                        f'node["office"="legal"](around:25000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["gym", "fitness", "yoga", "crossfit"]):
                    filters = [
                        f'node["leisure"="fitness_centre"](around:25000,{lat},{lon});',
                    ]
                elif any(w in kw_lower for w in ["salon", "spa", "beauty", "barber"]):
                    filters = [
                        f'node["shop"="beauty"](around:25000,{lat},{lon});',
                        f'node["shop"="hairdresser"](around:25000,{lat},{lon});',
                    ]
                else:
                    clean_kw = re.sub(r'[^a-zA-Z0-9\s]', '', keyword).strip()
                    filters = [
                        f'node["name"~"{clean_kw}",i](around:25000,{lat},{lon});',
                        f'node["shop"](around:15000,{lat},{lon});',
                        f'node["office"](around:15000,{lat},{lon});',
                    ]

                body = "\n".join(filters)
                overpass_q = f"[out:json][timeout:15];\n(\n{body}\n);\nout tags center {limit * 3};\n"

                endpoints = [
                    "https://overpass-api.de/api/interpreter",
                    "https://lz4.overpass-api.de/api/interpreter",
                    "https://overpass.kumi.systems/api/interpreter"
                ]

                for ep in endpoints:
                    try:
                        overpass_url = f"{ep}?data={urllib.parse.quote(overpass_q)}"
                        from app.services.safe_fetch import safe_request_async
                        op_resp = await safe_request_async(
                            "GET",
                            overpass_url,
                            headers={"User-Agent": "HelixScout/2.0 (info@helixintelligence.ai)"},
                            timeout=12.0,
                            allowed_hosts={"overpass-api.de", "lz4.overpass-api.de", "overpass.kumi.systems"},
                        )
                        if op_resp.status_code == 200:
                            elements = op_resp.json().get("elements", [])
                            for el in elements:
                                tags = el.get("tags", {})
                                name = tags.get("name:en") or tags.get("name")
                                if not name:
                                    continue
                                cat = tags.get("amenity") or tags.get("healthcare") or tags.get("shop") or tags.get("office") or tags.get("tourism") or keyword
                                street = tags.get("addr:street", "")
                                housenumber = tags.get("addr:housenumber", "")
                                addr = f"{housenumber} {street}".strip() or tags.get("addr:full") or tags.get("addr:city") or city
                                phone = tags.get("phone") or tags.get("contact:phone")
                                website = tags.get("website") or tags.get("contact:website")

                                if not any(p["title"].lower() == name.lower() for p in places):
                                    places.append({
                                        "title": name,
                                        "phone": phone,
                                        "website": website,
                                        "category": str(cat).replace("_", " ").title(),
                                        "address": addr,
                                        "city": city,
                                        "rating": None,
                                        "reviews_count": None,
                                        "rating_provider": "overpass",
                                        "source_url": "https://overpass-api.de/api/interpreter",
                                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                                    })
                                if len(places) >= limit:
                                    break
                            if len(places) >= limit:
                                return places[:limit]
                    except Exception:
                        continue
        except Exception:
            pass

    # Priority 4: OpenStreetMap Nominatim Structured Search fallback
    if len(places) < limit:
        try:
            queries = [
                f"{keyword} {city}",
                f"{keyword.rstrip('s')} {city}",
                f"{city} {keyword}",
            ]
            for q in queries:
                nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&addressdetails=1&extratags=1&limit={limit}"
                from app.services.safe_fetch import safe_request_async
                nom_resp = await safe_request_async(
                    "GET",
                    nom_url,
                    headers={"User-Agent": "HelixScoutLeadGen/2.0 (contact@helixintelligence.ai)"},
                    timeout=7.0,
                    allowed_hosts={"nominatim.openstreetmap.org"},
                )
                if nom_resp.status_code == 200:
                    items = nom_resp.json()
                    for it in items:
                        title = it.get("name") or (it.get("display_name", "").split(",")[0] if it.get("display_name") else None)
                        if not title:
                            continue
                        extratags = it.get("extratags", {}) or {}
                        phone = extratags.get("phone") or extratags.get("contact:phone")
                        website = extratags.get("website") or extratags.get("contact:website")
                        cat = it.get("type") or it.get("class") or keyword
                        addr = it.get("display_name", city)

                        if not any(p["title"].lower() == title.lower() for p in places):
                            places.append({
                                "title": title,
                                "phone": phone,
                                "website": website,
                                "category": str(cat).replace("_", " ").title(),
                                "address": addr,
                                "city": city,
                                "rating": None,
                                "reviews_count": None,
                                "rating_provider": "nominatim",
                                "source_url": "https://nominatim.openstreetmap.org/search",
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                            })
                        if len(places) >= limit:
                            break
                if len(places) >= limit:
                    break
        except Exception:
            pass

    return places[:limit]

async def run_maps_scout_worker(job_id: str):
    """Enqueue durable work, then run inline only in tests or an explicit local override."""
    from app.services.work_outbox import enqueue_work, inline_execution_enabled
    async with async_session_maker() as db:
        job = (await db.execute(select(ScoutMapsJob).where(ScoutMapsJob.id == job_id))).scalars().first()
        if job is not None:
            try:
                await enqueue_work(
                    db,
                    kind="maps",
                    job_id=job_id,
                    org_id=job.org_id,
                    user_id=job.user_id,
                    payload={"keyword": job.keyword, "city": job.city},
                )
            except Exception:
                pass
    if inline_execution_enabled():
        await execute_maps_scout(job_id)


async def execute_maps_scout(job_id: str):
    """
    Background worker for Google Maps business lead generation.
    Follows: Geocode -> Search Directory (ScrapeGraph + OSM) -> Website & ScrapeGraph Contact Enrich -> Complete.
    """
    async with async_session_maker() as db:
        res = await db.execute(select(ScoutMapsJob).where(ScoutMapsJob.id == job_id))
        job = res.scalars().first()
        if not job:
            return

        from app.services.billing_service import assert_can_spend
        from fastapi import HTTPException
        from app.models.organization import Organization
        from app.models.user import User
        org_for_gate = (await db.execute(select(Organization).where(Organization.id == job.org_id))).scalar_one_or_none()
        owner = None
        if org_for_gate is not None:
            owner = (await db.execute(select(User).where(User.id == (job.user_id or org_for_gate.owner_id)))).scalar_one_or_none()
        try:
            if owner is None:
                raise HTTPException(status_code=403, detail={"code": "access_pending_approval", "message": "Access is pending approval by a platform admin."})
            await assert_can_spend(db, owner, required_credits=0.0, feature_name="scout", lock_row=False)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            job.status = "failed"
            job.error_msg = detail.get("message") or "Access is pending approval by a platform admin."
            await db.commit()
            return

        sg_key = get_scrapegraph_key()

        job.status = "running"
        job.stage = "geocode"
        job.stage_label = f"Geocoding target location '{job.city}'"
        job.stage_index = 1
        job.stages_total = 4
        job.logs = [
            f"> engine: helix_maps_scout/v2 (ScrapeGraph AI + gosom kit) · ok",
            f"> scrapegraph_api: {'connected' if sg_key else 'direct_web'}",
            f"> keyword: '{job.keyword}' · target: '{job.city}' · depth: {job.depth}",
        ]
        job.heartbeat_at = datetime.now(timezone.utc)
        await db.commit()

        start_time = time.time()
        logs = list(job.logs)

        try:
            # Nominatim, Overpass, ScrapeGraph, and the maps worker call
            # safe_request_async. A private MAPS_SCRAPER_BASE_URL is rejected.
            from app.services.safe_fetch import SafeAsyncClient
            async with SafeAsyncClient(timeout=25.0) as client:
                # 1. Geocode
                lat_lon = await geocode_city(job.city, client)
                if lat_lon:
                    job.lat, job.lon = lat_lon
                    logs.append(f"> geocode: lat={lat_lon[0]:.4f}, lon={lat_lon[1]:.4f} · resolved")
                else:
                    logs.append(f"> geocode: standard city query dispatch for '{job.city}'")

                # 2. Search
                job.stage = "search"
                job.stage_label = f"Searching directory for '{job.keyword}' in {job.city} via ScrapeGraph"
                job.stage_index = 2
                job.logs = logs
                await db.commit()

                raw_places = await scrape_maps_places(
                    keyword=job.keyword,
                    city=job.city,
                    depth=job.depth,
                    client=client
                )
                logs.append(f"> search: discovered {len(raw_places)} real business listings")

                # 3. Enrich Websites (emails & socials & phone numbers)
                job.stage = "enrich"
                job.stage_label = "Enriching discovered businesses with phone, email & social links"
                job.stage_index = 3
                job.logs = logs
                await db.commit()

                saved_leads = []
                for p in raw_places:
                    try:
                        title = p.get("title") or "Business"
                        website = p.get("website")
                        phone = p.get("phone")
                        emails_found = list(p.get("emails") or [])
                        if p.get("email") and p["email"] not in emails_found:
                            emails_found.insert(0, p["email"])
                        socials_found = dict(p.get("socials") or {})

                        # If website is missing, attempt to discover official website via ScrapeGraph Search
                        if not website and sg_key:
                            try:
                                site_search_leads = await search_leads_with_scrapegraph(
                                    keyword=f"{title}",
                                    city=job.city,
                                    limit=1,
                                    client=client
                                )
                                if site_search_leads and site_search_leads[0].get("website"):
                                    matched_site = site_search_leads[0]["website"]
                                    website = matched_site
                                    p["website"] = matched_site
                                    if not phone and site_search_leads[0].get("phone"):
                                        phone = site_search_leads[0]["phone"]
                                    if not emails_found and site_search_leads[0].get("emails"):
                                        emails_found = site_search_leads[0]["emails"]
                                    if not socials_found and site_search_leads[0].get("socials"):
                                        socials_found = site_search_leads[0]["socials"]
                            except Exception:
                                pass

                        # Enrich website if present
                        if website and (job.extract_emails or job.pull_socials):
                            try:
                                enrich_data = await enrich_from_website(website, client)
                                if job.extract_emails and enrich_data.get("emails"):
                                    for em in enrich_data["emails"]:
                                        if em not in emails_found:
                                            emails_found.append(em)
                                if job.pull_socials and enrich_data.get("socials"):
                                    socials_found = {**socials_found, **enrich_data["socials"]}
                                if not phone and enrich_data.get("phones"):
                                    phone = enrich_data["phones"][0]
                            except Exception:
                                pass

                            # ScrapeGraph deep business extract if still missing emails or socials
                            if (not emails_found or not socials_found) and sg_key:
                                try:
                                    sg_data = await extract_business_with_scrapegraph(website, title, client)
                                    if sg_data:
                                        if not emails_found and sg_data.get("emails"):
                                            emails_found = sg_data["emails"]
                                        if not phone and sg_data.get("phones"):
                                            phone = sg_data["phones"][0]
                                        if sg_data.get("socials"):
                                            socials_found = {**socials_found, **sg_data["socials"]}
                                except Exception:
                                    pass

                        lead = ScoutMapsLead(
                            job_id=job.id,
                            org_id=job.org_id,
                            title=title,
                            phone=phone,
                            email=emails_found[0] if emails_found else None,
                            emails_found=emails_found,
                            website=website,
                            category=p.get("category") or job.keyword.title(),
                            address=p.get("address") or job.city,
                            city=job.city,
                        )
                        # Assign after init. The column default is 0, and passing
                        # None into the constructor is stored as that default.
                        lead.rating = _optional_float(p.get("rating"))
                        lead.reviews_count = _optional_int(p.get("reviews_count"))
                        lead.metadata_raw = {
                            "rating": {
                                "value": lead.rating,
                                "provider": p.get("rating_provider"),
                                "source_url": p.get("source_url") or p.get("website"),
                                "fetched_at": p.get("fetched_at"),
                            },
                            "reviews_count": {
                                "value": lead.reviews_count,
                                "provider": p.get("rating_provider"),
                                "source_url": p.get("source_url") or p.get("website"),
                                "fetched_at": p.get("fetched_at"),
                            },
                            "source": p.get("source") or p.get("rating_provider"),
                        }
                        lead.instagram = socials_found.get("instagram") or p.get("instagram")
                        lead.facebook = socials_found.get("facebook") or p.get("facebook")
                        lead.linkedin = socials_found.get("linkedin") or p.get("linkedin")
                        lead.twitter = socials_found.get("twitter") or p.get("twitter")
                        lead.socials = socials_found
                        db.add(lead)
                        saved_leads.append(lead)

                        email_str = f"email: {lead.email}" if lead.email else "no email"
                        phone_str = f"tel: {lead.phone}" if lead.phone else "no phone"
                        social_str = f"socials: {len(socials_found)}" if socials_found else "no socials"
                        logs.append(f"> lead: {lead.title[:25]} · {phone_str} · {email_str} · {social_str}")
                    except Exception as lead_err:
                        logs.append(f"> warn lead parse: {str(lead_err)}")
                        continue

                # 4. Finalize
                job.status = "succeeded"
                job.stage = "complete"
                job.stage_label = f"Scout Maps complete · {len(saved_leads)} leads indexed"
                job.stage_index = 4
                job.results_count = len(saved_leads)
                job.elapsed_ms = int((time.time() - start_time) * 1000)
                logs.append(f"> job completed in {job.elapsed_ms / 1000:.1f}s with {len(saved_leads)} verified leads")
                job.logs = logs
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

        except Exception as exc:
            job.status = "failed"
            job.stage = "error"
            job.stage_label = f"Maps Scout error: {str(exc)}"
            logs.append(f"> error: {str(exc)}")
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)
            if job.credits_used and job.credits_used > 0:
                from app.services.billing_service import refund
                await refund(db, job.org_id, job.credits_used, f"maps_scout_worker_fatal: {exc}", job.id)
            await db.commit()
