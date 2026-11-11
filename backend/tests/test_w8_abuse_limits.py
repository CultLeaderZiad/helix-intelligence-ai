"""W8: rate limits on abuse-prone routes, and the production proxy default.

No database: these drive the middleware directly with a tiny app.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import effective_trusted_proxy_cidrs, settings
from app.middleware.rate_limit import RateLimitMiddleware


def _client(paths):
    app = FastAPI()
    for path in paths:
        app.add_api_route(path, lambda: {"ok": True}, methods=["GET", "POST"])
    app.add_middleware(RateLimitMiddleware)
    return TestClient(app)


def _codes(client, method, path, n, ip="203.0.113.7"):
    return [client.request(method, path, headers={"x-forwarded-for": ip}).status_code for _ in range(n)]


def test_support_tickets_are_limited(monkeypatch):
    monkeypatch.setattr(settings, "ABUSE_RATE_LIMIT", 3)
    client = _client(["/api/support/tickets"])
    assert _codes(client, "POST", "/api/support/tickets", 4) == [200, 200, 200, 429]


def test_each_abuse_route_is_covered(monkeypatch):
    monkeypatch.setattr(settings, "ABUSE_RATE_LIMIT", 1)
    paths = ["/api/account/access-requests", "/api/boards/share-links", "/api/discovery/drafts"]
    client = _client(paths)
    for path in paths:
        assert _codes(client, "POST", path, 2) == [200, 429], path


def test_monitor_runs_share_the_paid_bucket(monkeypatch):
    monkeypatch.setattr(settings, "EXPENSIVE_RATE_LIMIT", 2)
    client = _client(["/api/monitors/m1/run", "/api/discovery/jobs"])
    assert _codes(client, "POST", "/api/monitors/m1/run", 1) == [200]
    assert _codes(client, "POST", "/api/discovery/jobs", 2) == [200, 429]


def test_guest_board_reads_are_limited(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT", 2)
    client = _client(["/api/public/boards/{token}"])
    assert _codes(client, "GET", "/api/public/boards/abc", 3) == [200, 200, 429]


def test_signed_in_reads_are_not_limited(monkeypatch):
    monkeypatch.setattr(settings, "ABUSE_RATE_LIMIT", 1)
    client = _client(["/api/support/tickets"])
    assert _codes(client, "GET", "/api/support/tickets", 5) == [200] * 5


def test_production_trusts_render_proxy_by_default(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert effective_trusted_proxy_cidrs(settings) == "10.0.0.0/8"
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert effective_trusted_proxy_cidrs(settings) == ""
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "192.168.0.0/16")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert effective_trusted_proxy_cidrs(settings) == "192.168.0.0/16"


def test_production_clients_behind_render_get_separate_buckets(monkeypatch):
    """The bug this fixes: behind Render's proxy every caller shared one bucket."""
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT", 1)
    app = FastAPI()
    app.add_api_route("/api/auth/sign-in", lambda: {"ok": True}, methods=["POST"])
    app.add_middleware(RateLimitMiddleware)
    client = TestClient(app, client=("10.1.2.3", 50000))
    assert _codes(client, "POST", "/api/auth/sign-in", 2, ip="198.51.100.1") == [200, 429]
    assert _codes(client, "POST", "/api/auth/sign-in", 1, ip="198.51.100.2") == [200]
