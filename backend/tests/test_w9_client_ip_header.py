"""Client IP behind Render + Cloudflare, built from the masked probe lines
observed on 2026-11-12 (docs/SECURITY_AUDIT.md A1). Addresses are
documentation ranges standing in for the masked real ones."""
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.core import config
from app.middleware import rate_limit
from app.middleware.rate_limit import client_ip

REAL_A = "198.51.100.7"     # stands in for the real 197.37.x.x
REAL_B = "198.51.100.99"    # a second real client
FORGED = "203.0.113.77"
CF_HOP = "172.71.0.10"
RENDER_HOP = "10.28.0.5"


def _req(peer, headers):
    scope = {
        "type": "http", "method": "GET", "path": "/api/health", "query_string": b"",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 0),
    }
    return Request(scope)


def _observed(real, forged=None):
    """Headers as seen on Render; uvicorn has already rewritten the peer
    to the leftmost X-Forwarded-For entry."""
    xff = f"{real}, {CF_HOP}, {RENDER_HOP}"
    if forged:
        xff = f"{forged},{xff}"
    return _req(forged or real, {
        "x-forwarded-for": xff,
        "true-client-ip": real,
        "cf-connecting-ip": real,
        "x-forwarded-proto": "https",
    })


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(rate_limit.settings, "CLIENT_IP_HEADER", "")
    monkeypatch.setattr(rate_limit.settings, "TRUSTED_PROXY_CIDRS", "")


def test_forged_leftmost_xff_is_ignored(production):
    assert client_ip(_observed(REAL_A, forged=FORGED)) == REAL_A


def test_two_real_clients_get_separate_buckets(production):
    assert client_ip(_observed(REAL_A)) == REAL_A
    assert client_ip(_observed(REAL_B)) == REAL_B


def test_forged_requests_share_the_real_clients_bucket(production):
    ips = {client_ip(_observed(REAL_A, forged=f"203.0.113.{n}")) for n in range(1, 30)}
    assert ips == {REAL_A}


def test_missing_or_invalid_header_falls_back_to_peer(production):
    assert client_ip(_req(REAL_B, {})) == REAL_B
    assert client_ip(_req(REAL_B, {"cf-connecting-ip": "not-an-ip"})) == REAL_B


def test_header_choice():
    eff = config.effective_client_ip_header
    assert eff(SimpleNamespace(ENVIRONMENT="production", CLIENT_IP_HEADER="")) == "cf-connecting-ip"
    assert eff(SimpleNamespace(ENVIRONMENT="development", CLIENT_IP_HEADER="")) == ""
    assert eff(SimpleNamespace(ENVIRONMENT="production", CLIENT_IP_HEADER="none")) == ""
    assert eff(SimpleNamespace(ENVIRONMENT="development", CLIENT_IP_HEADER="True-Client-IP")) == "true-client-ip"


def test_render_counts_as_production_like_the_docs_gate(monkeypatch):
    """Render runs with an ENVIRONMENT alias; the header must still apply."""
    eff = config.effective_client_ip_header
    monkeypatch.setenv("RENDER", "true")
    assert eff(SimpleNamespace(ENVIRONMENT="development", CLIENT_IP_HEADER="")) == "cf-connecting-ip"
    monkeypatch.delenv("RENDER")
    assert eff(SimpleNamespace(ENVIRONMENT="prod", CLIENT_IP_HEADER="")) == "cf-connecting-ip"
    assert eff(SimpleNamespace(ENVIRONMENT="bogus", CLIENT_IP_HEADER="")) == ""
