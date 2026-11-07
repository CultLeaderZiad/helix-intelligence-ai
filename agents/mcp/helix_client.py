"""Read-only Helix client used by the MCP server.

Every call is a GET against the Helix API with ``Accept: text/markdown`` and
the user's own bearer token, so the API applies the same workspace RLS and
feature flags as the web app. Nothing here can start a search, spend credits,
or write anything: there is no POST/PATCH/DELETE in this module.
"""
from __future__ import annotations

import os
from typing import Optional
from urllib.parse import quote

import httpx

READ_ONLY_METHOD = "GET"


class HelixError(RuntimeError):
    pass


class HelixClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, transport=None):
        self.base_url = (base_url or os.environ.get("HELIX_API_URL") or "").rstrip("/")
        self.token = token or os.environ.get("HELIX_ACCESS_TOKEN") or ""
        if not self.base_url:
            raise HelixError("Set HELIX_API_URL, e.g. https://<your-api-host>/api")
        if not self.token:
            raise HelixError("Set HELIX_ACCESS_TOKEN to your own Helix session token")
        self._http = httpx.Client(timeout=30, transport=transport)

    def _get(self, path: str, params: Optional[dict] = None) -> str:
        response = self._http.request(
            READ_ONLY_METHOD,
            f"{self.base_url}{path}",
            params={k: v for k, v in (params or {}).items() if v not in (None, "", 0)},
            headers={"Authorization": f"Bearer {self.token}", "Accept": "text/markdown"},
        )
        if response.status_code == 404:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            return f"_Not found: {detail or 'nothing matches in your workspace.'}_"
        if response.status_code in (401, 403):
            return "_Not allowed: the token is expired or this workspace is not granted this feature._"
        if response.status_code >= 400:
            raise HelixError(f"Helix API returned HTTP {response.status_code}")
        return response.text

    def search_ads(self, query: str, min_days: int = 0, sort: str = "days_active_desc", page: int = 1) -> str:
        return self._get("/discovery/stored-results", {"query": query, "min_days": min_days, "sort": sort, "page": page})

    def get_board(self, board: str) -> str:
        return self._get("/boards/items", {"collection": board})

    def list_monitor_changes(self, monitor_id: Optional[str] = None, limit: int = 50) -> str:
        return self._get("/monitors/events", {"monitor_id": monitor_id, "limit": limit})

    def get_ad(self, ad_id: str) -> str:
        return self._get(f"/creatives/{quote(ad_id, safe='')}")
