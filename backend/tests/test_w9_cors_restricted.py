"""CORS allows only the methods and headers the SPA uses; origins unchanged.

Builds the same CORSMiddleware the app adds, with main's method and header
lists, and sends browser preflights. No database.
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import main

ORIGIN = "https://app.example.test"


def _app():
    app = FastAPI()
    app.add_api_route("/api/x", lambda: {"ok": True}, methods=["GET", "POST"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGIN],
        allow_credentials=True,
        allow_methods=list(main.CORS_ALLOW_METHODS),
        allow_headers=list(main.CORS_ALLOW_HEADERS),
    )
    return app


def _preflight(method, headers):
    async def go():
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.options("/api/x", headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": headers,
            })

    return asyncio.run(go())


def test_lists_are_explicit_not_wildcards():
    assert "*" not in main.CORS_ALLOW_METHODS and "*" not in main.CORS_ALLOW_HEADERS
    assert {"Authorization", "Content-Type"} <= set(main.CORS_ALLOW_HEADERS)
    assert set(main.CORS_ALLOW_METHODS) == {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


def test_spa_preflight_is_allowed():
    r = _preflight("POST", "authorization,content-type")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGIN


def test_unused_method_and_header_are_refused():
    assert _preflight("TRACE", "authorization").status_code == 400
    assert _preflight("POST", "x-admin-secret").status_code == 400


def test_main_app_uses_the_restricted_lists():
    cors = [m for m in main.app.user_middleware if m.cls is CORSMiddleware]
    for middleware in cors:
        assert middleware.kwargs["allow_methods"] == list(main.CORS_ALLOW_METHODS)
        assert middleware.kwargs["allow_headers"] == list(main.CORS_ALLOW_HEADERS)
