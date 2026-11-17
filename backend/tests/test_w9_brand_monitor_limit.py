"""W9 rebase: POST /api/monitors/brand spends like the other monitor routes.

Driven over HTTP (httpx ASGITransport) through the real router and the real
``account_rate_limit`` dependency. No database: auth, entitlement and the
monitor service are stubbed, so only the limiter decides the status code.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

from app.api.routers import monitors
from app.core import limits
from app.core.config import settings
from app.core.deps import get_current_user, get_db


def _app(monkeypatch, user_id="u_brand_limit"):
    async def _no_entitlement_check(*_a, **_k):
        return None

    async def _org(_db, _user):
        return "o_brand_limit"

    async def _create(_db, **kwargs):
        return {"id": "m1", "query": kwargs["query"], "name": kwargs["name"]}

    monkeypatch.setattr("app.services.billing_service.assert_can_spend", _no_entitlement_check)
    monkeypatch.setattr(monitors, "_org_id", _org)
    monkeypatch.setattr(monitors.monitor_service, "create_monitor", _create)

    app = FastAPI()
    app.include_router(monitors.router, prefix="/api/monitors")

    async def _db():
        yield None

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _post(app, n):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return [
                (await c.post("/api/monitors/brand", json={"page_id": "123456789"})).status_code
                for _ in range(n)
            ]

    return asyncio.run(go())


def test_brand_monitor_route_uses_the_monitor_spend_dependencies():
    route = next(r for r in monitors.router.routes if r.path == "/brand" and "POST" in r.methods)
    assert len(route.dependencies) == len(monitors._monitor_spend)


def test_brand_monitor_creation_returns_429_past_the_per_account_limit(monkeypatch):
    limits.reset()
    monkeypatch.setattr(settings, "ACCOUNT_MONITOR_LIMIT", 2)
    monkeypatch.setattr(settings, "ACCOUNT_MONITOR_WINDOW_S", 300)
    try:
        assert _post(_app(monkeypatch), 3) == [201, 201, 429]
    finally:
        limits.reset()


def test_brand_monitor_limit_is_per_account_not_shared(monkeypatch):
    limits.reset()
    monkeypatch.setattr(settings, "ACCOUNT_MONITOR_LIMIT", 1)
    try:
        assert _post(_app(monkeypatch, "u_a"), 2) == [201, 429]
        assert _post(_app(monkeypatch, "u_b"), 1) == [201]
    finally:
        limits.reset()
