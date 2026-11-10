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










def _urls(calls):
    found = []
    for args in calls:
        destination = args[1]
        found.append(getattr(destination, "url", str(destination)))
    return found








