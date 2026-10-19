"""Each converted outbound path rejects loopback redirects and private addresses."""

from __future__ import annotations

import os
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import settings
from app.services.safe_fetch import UnsafeFetch
from app.services.scraping.base import ProviderFailure


def _public_resolve(hostname, port):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _private_resolve(hostname, port):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]


def _redirect_exchange(*_args, **_kwargs):
    return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"}, content=b"")


@pytest.fixture
def redirect_guard():
    calls = []

    def exchange(*args, **kwargs):
        calls.append(args[1].url if len(args) > 1 else kwargs.get("url"))
        return _redirect_exchange()

    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=exchange
    ):
        yield calls


@pytest.fixture
def private_guard():
    calls = []

    def exchange(*args, **kwargs):
        calls.append(args)
        return httpx.Response(200, content=b"ok")

    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=exchange
    ):
        yield calls


@pytest.mark.asyncio
async def test_meta_graph_rejects_redirect_and_private_ip(redirect_guard, private_guard):
    from app.services.scraping.ad_library_provider import AdLibraryProvider

    provider = AdLibraryProvider()
    provider.meta_token = "meta-test-token"
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: (_redirect_exchange(), redirect_guard.append(a))[0]
    ):
        assert await provider.query_meta_api("nike") == []
        assert len(redirect_guard) == 1
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: private_guard.append(a)
    ):
        assert await provider.query_meta_api("nike") == []
        assert private_guard == []


@pytest.mark.asyncio
async def test_apify_rejects_redirect_and_private_ip():
    from app.services.scraping.ad_library_provider import AdLibraryProvider

    provider = AdLibraryProvider()
    provider.apify_token = "apify-test-token"
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await provider.query_apify("nike") == []
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        assert await provider.query_apify("nike") == []
        assert calls == []


@pytest.mark.asyncio
async def test_adyntel_rejects_redirect_and_private_ip():
    from app.services.scraping.adyntel_provider import AdyntelProvider

    provider = AdyntelProvider(None, "org", "user")
    provider.adyntel_api_key = "adyntel-key"
    provider.adyntel_email = "owner@example.com"
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        with pytest.raises(ProviderFailure) as raised:
            await provider.search("nike.com", max_records=5)
        assert raised.value.provider == "adyntel"
        assert provider.last_outcome == "failure"
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        with pytest.raises(ProviderFailure):
            await provider.search("nike.com", max_records=5)
        assert provider.last_outcome == "failure"
        assert calls == []


@pytest.mark.asyncio
async def test_metapi_rejects_redirect_and_private_ip():
    from app.services.scraping.metapi_provider import MetapiProvider

    provider = MetapiProvider(None, "org", "user")
    provider.metapi_api_key = "metapi-key"
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await provider.search("nike", max_records=5) == []
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        assert await provider.search("nike", max_records=5) == []
        assert calls == []


@pytest.mark.asyncio
async def test_scrapegraph_provider_rejects_redirect_and_private_ip():
    from app.services.scraping.scrapegraph_provider import ScrapeGraphProvider

    provider = ScrapeGraphProvider()
    provider.api_key = "sg-key"
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        result = await provider.extract_landing_page("https://example.com/landing")
        assert result["status"] == "failure"
        assert result.get("headline") is None
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        result = await provider.extract_landing_page("https://example.com/landing")
        assert result["status"] == "failure"
        assert calls == []


def test_robots_fetch_rejects_redirect_and_private_ip():
    from app.services import scrapling_engine as engine

    engine._ROBOTS_CACHE.clear()
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert engine.robots_allowed("https://example.com/page") is True
        assert len(calls) == 1
    engine._ROBOTS_CACHE.clear()
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        assert engine.robots_allowed("https://private-robots.example/page") is True
        assert calls == []
    engine._ROBOTS_CACHE.clear()


def test_scrapling_sdk_refuses_private_initial_url():
    from app.services.scrapling_engine import fetch

    with patch("app.services.safe_fetch._resolve", _private_resolve):
        result = fetch("https://rebind.example/path", engine="http", robots_obey=False)
    assert result["reason"] == "unsafe_url"
    assert result["html"] is None


@pytest.mark.asyncio
async def test_scout_client_rejects_redirect_and_private_ip():
    from app.services.safe_fetch import SafeAsyncClient

    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        client = SafeAsyncClient(timeout=5.0)
        with pytest.raises(UnsafeFetch, match="SSRF blocked"):
            await client.get("https://api.github.com/users/octocat")
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        client = SafeAsyncClient(timeout=5.0)
        with pytest.raises(UnsafeFetch, match="SSRF blocked"):
            await client.get("https://api.github.com/users/octocat")
        assert calls == []


@pytest.mark.asyncio
async def test_nominatim_geocode_rejects_redirect_and_private_ip():
    from app.services.maps_scout_service import geocode_city

    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await geocode_city("not-a-cached-city-w0", client=None) is None
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        assert await geocode_city("not-a-cached-city-w0", client=None) is None
        assert calls == []


@pytest.mark.asyncio
async def test_scrapegraph_lead_extract_rejects_redirect_and_private_ip():
    from app.services import scrapegraph_lead_service as mod

    calls = []
    with patch.object(mod, "get_scrapegraph_key", return_value="sg-key"), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await mod.extract_profile_with_scrapegraph("https://example.com/profile") == {}
        assert len(calls) == 1
    calls.clear()
    with patch.object(mod, "get_scrapegraph_key", return_value="sg-key"), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        assert await mod.extract_profile_with_scrapegraph("https://example.com/profile") == {}
        assert calls == []


@pytest.mark.asyncio
async def test_entity_groq_rejects_redirect_and_private_ip():
    from app.services.entity_intelligence import analyze_entity_intent

    calls = []
    with patch.object(settings, "GROQ_API_KEY", "groq-test"), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        result = await analyze_entity_intent("zz-w0-unique-brand")
        assert "LOOPBACK" not in str(result)
        assert len(calls) == 1
    calls.clear()
    with patch.object(settings, "GROQ_API_KEY", "groq-test"), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        await analyze_entity_intent("zz-w0-unique-brand")
        assert calls == []


@pytest.mark.asyncio
async def test_query_translator_rejects_redirect_and_private_ip():
    from app.services.query_translator import translate_search_query

    calls = []
    with patch.object(settings, "GROQ_API_KEY", "groq-test"), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await translate_search_query("حذاء رياضي", "en") == "حذاء رياضي"
        assert len(calls) == 1
    calls.clear()
    with patch.object(settings, "GROQ_API_KEY", "groq-test"), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        await translate_search_query("حذاء رياضي", "en")
        assert calls == []


@pytest.mark.asyncio
async def test_byok_rejects_redirect_and_private_ip():
    from app.services.ai.byok_provider import BYOKProvider

    provider = BYOKProvider("sk-test", provider_choice="openai")
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        with pytest.raises(Exception):
            await provider._call_api([{"role": "user", "content": "hi"}])
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        with pytest.raises(Exception):
            await provider._call_api([{"role": "user", "content": "hi"}])
        assert calls == []


@pytest.mark.asyncio
async def test_pollinations_image_rejects_redirect_and_private_ip():
    from app.services.ai.pollinations_provider import PollinationsProvider

    provider = PollinationsProvider()
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        with pytest.raises(Exception):
            await provider.generate_image("studio product")
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        with pytest.raises(Exception):
            await provider.generate_image("studio product")
        assert calls == []


@pytest.mark.asyncio
async def test_hunter_domain_search_rejects_redirect_and_private_ip():
    from app.services.leadgen_pipeline import _hunter_domain_search

    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        with pytest.raises(UnsafeFetch, match="SSRF blocked"):
            await _hunter_domain_search("example.com", "hunter-key")
        assert len(calls) == 1
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        with pytest.raises(UnsafeFetch, match="SSRF blocked"):
            await _hunter_domain_search("example.com", "hunter-key")
        assert calls == []


@pytest.mark.asyncio
async def test_leadgen_worker_health_rejects_redirect_and_private_ip():
    from app.api.routers.leadgen import _is_worker_available

    db = AsyncMock()
    calls = []
    with patch.object(settings, "SCRAPLING_INLINE_WORKER", False), patch.object(
        settings, "SCRAPLING_WORKER_ENABLED", True
    ), patch.object(settings, "SCRAPLING_WORKER_URL", "https://worker.example/base"), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
        assert await _is_worker_available(db) is False
        assert len(calls) == 1
    calls.clear()
    with patch.object(settings, "SCRAPLING_INLINE_WORKER", False), patch.object(
        settings, "SCRAPLING_WORKER_ENABLED", True
    ), patch.object(settings, "SCRAPLING_WORKER_URL", "https://worker.example/base"), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
        assert await _is_worker_available(db) is False
        assert calls == []


def _urls(calls):
    found = []
    for args in calls:
        destination = args[1]
        found.append(getattr(destination, "url", str(destination)))
    return found


@pytest.mark.asyncio
async def test_maps_worker_rejects_redirect_and_private_ip():
    from app.services import maps_scout_service as mod

    calls = []
    env = {"MAPS_SCRAPER_BASE_URL": "https://maps-worker.example", "MAPS_SCRAPER_API_KEY": "worker-key"}
    with patch.object(mod, "get_scrapegraph_key", return_value=None), patch.dict(os.environ, env), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await mod.scrape_maps_places("dentists", "not-a-cached-city-w0", 1, client=None) == []
        urls = _urls(calls)
        assert urls and urls[0].startswith("https://maps-worker.example/")
        assert all("127.0.0.1" not in url for url in urls)
    calls.clear()
    with patch.object(mod, "get_scrapegraph_key", return_value=None), patch.dict(os.environ, env), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        assert await mod.scrape_maps_places("dentists", "not-a-cached-city-w0", 1, client=None) == []
        assert calls == []


@pytest.mark.asyncio
async def test_overpass_rejects_redirect_and_private_ip():
    from app.services import maps_scout_service as mod

    calls = []
    with patch.object(mod, "get_scrapegraph_key", return_value=None), patch.dict(
        os.environ, {"MAPS_SCRAPER_BASE_URL": ""}, clear=False
    ), patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await mod.scrape_maps_places("dentist", "dubai", 1, client=None) == []
        urls = _urls(calls)
        assert any("overpass-api.de" in url for url in urls)
        assert all("127.0.0.1" not in url for url in urls)
    calls.clear()
    with patch.object(mod, "get_scrapegraph_key", return_value=None), patch.dict(
        os.environ, {"MAPS_SCRAPER_BASE_URL": ""}, clear=False
    ), patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        assert await mod.scrape_maps_places("dentist", "dubai", 1, client=None) == []
        assert calls == []


@pytest.mark.asyncio
async def test_scrapegraph_search_and_business_reject_redirect_and_private_ip():
    from app.services import scrapegraph_lead_service as mod

    calls = []
    with patch.object(mod, "get_scrapegraph_key", return_value="sg-key"), patch(
        "app.services.safe_fetch._resolve", _public_resolve
    ), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        assert await mod.search_leads_with_scrapegraph("dentists", "dubai", limit=1) == []
        assert await mod.extract_business_with_scrapegraph("https://example.com") == {}
        assert len(calls) == 2
        assert all("127.0.0.1" not in url for url in _urls(calls))
    calls.clear()
    with patch.object(mod, "get_scrapegraph_key", return_value="sg-key"), patch(
        "app.services.safe_fetch._resolve", _private_resolve
    ), patch("app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)):
        assert await mod.search_leads_with_scrapegraph("dentists", "dubai", limit=1) == []
        assert await mod.extract_business_with_scrapegraph("https://example.com") == {}
        assert calls == []


@pytest.mark.asyncio
async def test_pollinations_video_rejects_redirect_and_private_ip():
    from app.services.ai.pollinations_provider import PollinationsProvider

    provider = PollinationsProvider()
    calls = []
    with patch("app.services.safe_fetch._resolve", _public_resolve), patch(
        "app.services.safe_fetch._exchange",
        side_effect=lambda *a, **k: calls.append(a) or _redirect_exchange(),
    ):
        with pytest.raises(Exception):
            await provider.generate_video("studio product")
        assert len(calls) == 1
        assert all("127.0.0.1" not in url for url in _urls(calls))
    calls.clear()
    with patch("app.services.safe_fetch._resolve", _private_resolve), patch(
        "app.services.safe_fetch._exchange", side_effect=lambda *a, **k: calls.append(a)
    ):
        with pytest.raises(Exception):
            await provider.generate_video("studio product")
        assert calls == []
