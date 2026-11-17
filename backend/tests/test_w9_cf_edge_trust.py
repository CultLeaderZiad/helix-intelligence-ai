"""cf-connecting-ip is believed only when the request reached Render from a
Cloudflare address, or carries the shared edge secret.

Shapes follow the masked production probe (docs/SECURITY_AUDIT.md A1):
``x-forwarded-for: <client>, <cloudflare edge>, <render 10.x>`` with uvicorn's
peer rewritten to the leftmost entry. Documentation ranges stand in for real
client addresses.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.middleware import rate_limit
from app.middleware.rate_limit import RateLimitMiddleware, client_ip, edge_header_trusted

REAL = "198.51.100.7"
OTHER = "198.51.100.99"
FORGED = "203.0.113.77"
CF_HOP = "172.71.0.10"         # inside Cloudflare's 172.64.0.0/13
NOT_CF_HOP = "192.0.2.50"      # a caller that skipped Cloudflare
RENDER_HOP = "10.28.0.5"


def _req(peer, headers):
    return Request({
        "type": "http", "method": "GET", "path": "/api/health", "query_string": b"",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 0),
    })


def _via(edge_hop, cf_ip, forged=None, extra=None):
    """A request as Render's app sees it after passing ``edge_hop``."""
    xff = f"{REAL}, {edge_hop}, {RENDER_HOP}"
    if forged:
        xff = f"{forged}, {xff}"
    headers = {"x-forwarded-for": xff, "cf-connecting-ip": cf_ip, **(extra or {})}
    return _req(forged or REAL, headers)


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(rate_limit.settings, "CLIENT_IP_HEADER", "")
    monkeypatch.setattr(rate_limit.settings, "TRUSTED_PROXY_CIDRS", "")
    monkeypatch.setattr(rate_limit.settings, "TRUSTED_PROXY_SECRET", "")


def test_cloudflare_ranges_are_parsed_and_cover_the_observed_hop():
    assert len(rate_limit.CLOUDFLARE_IP_RANGES) == 22
    assert rate_limit._is_cloudflare(CF_HOP)
    assert rate_limit._is_cloudflare("2606:4700::1")
    assert not rate_limit._is_cloudflare(NOT_CF_HOP)
    assert not rate_limit._is_cloudflare("not-an-ip")


def test_legitimate_cloudflare_header_is_used(production):
    assert edge_header_trusted(_via(CF_HOP, REAL))
    assert client_ip(_via(CF_HOP, REAL)) == REAL
    # A forged X-Forwarded-For prefix changes nothing (production regression from #42).
    assert client_ip(_via(CF_HOP, REAL, forged=FORGED)) == REAL


def test_forged_cf_connecting_ip_from_a_non_cloudflare_edge_is_ignored(production):
    request = _via(NOT_CF_HOP, OTHER)
    assert not edge_header_trusted(request)
    assert client_ip(request) != OTHER


def test_forged_header_on_a_direct_connection_is_ignored(production):
    request = _req(NOT_CF_HOP, {"cf-connecting-ip": OTHER})
    assert client_ip(request) == NOT_CF_HOP


def test_edge_secret_trusts_the_header_only_when_it_matches(production, monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "TRUSTED_PROXY_SECRET", "s3cret-edge-value")
    good = _via(NOT_CF_HOP, REAL, extra={"x-helix-edge-secret": "s3cret-edge-value"})
    bad = _via(NOT_CF_HOP, OTHER, extra={"x-helix-edge-secret": "wrong"})
    assert client_ip(good) == REAL
    assert client_ip(bad) != OTHER


def test_secret_is_off_by_default(production):
    request = _via(NOT_CF_HOP, OTHER, extra={"x-helix-edge-secret": ""})
    assert not edge_header_trusted(request)


def _codes(app, n, *, cf_ip, edge_hop, rotate_forged=False):
    async def go():
        out = []
        transport = httpx.ASGITransport(app=app, client=(REAL, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            for i in range(n):
                xff = f"{REAL}, {edge_hop}, {RENDER_HOP}"
                if rotate_forged:
                    xff = f"203.0.113.{i + 1}, {xff}"
                headers = {"x-forwarded-for": xff, "cf-connecting-ip": cf_ip}
                out.append((await c.post("/api/auth/sign-in", headers=headers)).status_code)
        return out

    return asyncio.run(go())


def _app():
    app = FastAPI()
    app.add_api_route("/api/auth/sign-in", lambda: {"ok": True}, methods=["POST"])
    app.add_middleware(RateLimitMiddleware)
    return app


def test_per_ip_429_still_triggers_behind_cloudflare(production, monkeypatch):
    rate_limit.reset_buckets()
    monkeypatch.setattr(rate_limit.settings, "AUTH_RATE_LIMIT", 2)
    try:
        assert _codes(_app(), 3, cf_ip=REAL, edge_hop=CF_HOP, rotate_forged=True) == [200, 200, 429]
    finally:
        rate_limit.reset_buckets()


def test_rotating_a_forged_cf_header_does_not_reset_the_bucket(production, monkeypatch):
    rate_limit.reset_buckets()
    monkeypatch.setattr(rate_limit.settings, "AUTH_RATE_LIMIT", 2)

    async def go():
        out = []
        transport = httpx.ASGITransport(app=_app(), client=(REAL, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            for i in range(3):
                headers = {
                    "x-forwarded-for": f"{REAL}, {NOT_CF_HOP}, {RENDER_HOP}",
                    "cf-connecting-ip": f"198.51.100.{i + 10}",
                }
                out.append((await c.post("/api/auth/sign-in", headers=headers)).status_code)
        return out

    try:
        assert asyncio.run(go()) == [200, 200, 429]
    finally:
        rate_limit.reset_buckets()
