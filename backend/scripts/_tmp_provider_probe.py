"""Probe each Discover-related provider. Prints counts/status only, never secrets."""
import os, sys, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from app.core.config import settings
from app.services.scraping.metapi_provider import MetapiProvider
from app.services.scraping.adyntel_provider import AdyntelProvider
from app.services.scraping.ad_library_provider import AdLibraryProvider
from app.services.scraping.scrapegraph_provider import ScrapeGraphProvider

QUERY = os.getenv("PROBE_QUERY", "Real madrid")


def present(name, value):
    print(f"  {name}: {'set' if bool(value) else 'MISSING'}")


async def probe_metapi(query: str):
    p = MetapiProvider(None, "", "")
    if not p.metapi_api_key:
        print("METAPI: skipped (no key)")
        return
    ads = await p.search(query, max_records=8)
    print(f"METAPI query={query!r} ads={len(ads)}")
    if ads:
        a = ads[0]
        headline = (a.headline or "").encode("ascii", "replace").decode("ascii")[:80]
        brand = (a.brand_name or "").encode("ascii", "replace").decode("ascii")
        print(f"  sample brand={brand!r} headline={headline!r} source={a.data_source}")


async def probe_adyntel(query: str):
    p = AdyntelProvider(None, "", "")
    if not (p.adyntel_api_key and p.adyntel_email):
        print("ADYNTEL: skipped (no key/email)")
        return
    ads = await p.search(query, max_records=8)
    print(f"ADYNTEL query={query!r} ads={len(ads)}")
    if ads:
        a = ads[0]
        headline = (a.headline or "").encode("ascii", "replace").decode("ascii")[:80]
        brand = (a.brand_name or "").encode("ascii", "replace").decode("ascii")
        print(f"  sample brand={brand!r} headline={headline!r} domain={a.landing_domain}")


async def probe_meta(query: str):
    p = AdLibraryProvider()
    if not p.meta_token:
        print("META_GRAPH: skipped (no token)")
        return
    ads = await p.query_meta_api(query, country="ALL", max_records=8)
    print(f"META_GRAPH query={query!r} ads={len(ads)}")


async def probe_scrapegraph(url: str):
    p = ScrapeGraphProvider()
    if not p.api_key:
        print("SCRAPEGRAPH: skipped (no key)")
        return
    data = await p.extract_landing_page(url)
    print(f"SCRAPEGRAPH url={url} keys={list(data.keys())} nonempty={bool(data)}")
    if data:
        print(f"  headline={(data.get('headline') or '')[:80]!r}")


async def probe_brightdata():
    key = (settings.BRIGHTDATA_API_KEY or "").strip().strip("\"'")
    if not key:
        print("BRIGHTDATA: skipped (no key)")
        return
    # Bright Data is not wired into Discover. This only checks whether the
    # key is accepted by their API, not whether it can search ads.
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get("https://api.brightdata.com/zone/list", headers=headers)
    print(f"BRIGHTDATA zone/list status={r.status_code} body={(r.text or '')[:160]}")


async def probe_chain(query: str):
    p = AdLibraryProvider()
    ads = await p.search(query, max_records=8)
    print(
        f"CHAIN query={query!r} tried={p.sources_tried} used={p.last_provider_used} ads={len(ads)}"
    )


async def main():
    print("local key presence")
    present("METAPI_API_KEY", settings.METAPI_API_KEY)
    present("ADYNTEL_API_KEY", getattr(settings, "ADYNTEL_API_KEY", "") or os.getenv("ADYNTEL_API_KEY"))
    present("ADYNTEL_EMAIL", getattr(settings, "ADYNTEL_EMAIL", "") or os.getenv("ADYNTEL_EMAIL"))
    present("META_ACCESS_TOKEN", settings.META_ACCESS_TOKEN)
    present("SCRAPEGRAPH_API_KEY", settings.SCRAPEGRAPH_API_KEY)
    present("BRIGHTDATA_API_KEY", settings.BRIGHTDATA_API_KEY)
    present("APIFY_API_TOKEN", settings.APIFY_API_TOKEN)
    present("APIFY_ENABLED", settings.APIFY_ENABLED)

    print("\n--- individual ---")
    await probe_metapi(QUERY)
    await probe_adyntel(QUERY)
    await probe_adyntel("nike.com")
    await probe_meta(QUERY)
    await probe_scrapegraph("https://www.realmadrid.com")
    await probe_brightdata()

    print("\n--- full chain ---")
    await probe_chain(QUERY)


asyncio.run(main())
