"""W8: Markdown views and the read-only MCP client use the app's honest labels and never write."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import httpx
import pytest
from starlette.requests import Request

from app.core import markdown

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agents" / "mcp"))
import helix_client  # noqa: E402


def _request(headers=None, query=b""):
    return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
                    "query_string": query, "method": "GET", "path": "/"})


def test_negotiation_by_accept_query_and_suffix():
    assert markdown.wants_markdown(_request({"accept": "text/markdown"}))
    assert markdown.wants_markdown(_request(query=b"format=md"))
    assert not markdown.wants_markdown(_request({"accept": "application/json"}))
    assert markdown.split_md("abc.md") == ("abc", True)
    assert markdown.split_md("abc") == ("abc", False)
    assert markdown.split_md(".md") == (".md", False)


def test_ads_table_keeps_unknown_unknown_and_rubric_labelled():
    items = [
        {"id": "a", "brand_name": "Acme", "headline": "Runs | long", "days_active": 45,
         "scores": {"composite": 7.25}, "metrics": {"impressions_est": 12000}, "permalink": "https://x/1"},
        {"id": "b", "brand_name": "Acme", "headline": "No start date", "days_active": None,
         "text_rubric_score": None, "impressions_est": None},
    ]
    md = markdown.ads_document("Competitor ads", items, meta=["Sort: days_active_desc"])
    assert "| 45 days |" in md and "| unknown |" in md and "0 days" not in md
    assert "7.2/10" in md or "7.3/10" in md
    assert "up to 12,000" in md and "Runs \\| long" in md
    assert "not a performance prediction" in md


def test_events_document_names_each_change():
    md = markdown.events_document([{"type": "killed_ad", "headline": "Old offer", "created_at": "2026-11-01"}])
    assert "Stopped running" in md and "Old offer" in md
    assert "baseline" in markdown.events_document([])


def test_mcp_client_only_ever_sends_get_with_markdown_accept():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="# ok")

    client = helix_client.HelixClient("http://api.test/api", "tok", transport=httpx.MockTransport(handler))
    client.search_ads("nike.com", min_days=30)
    client.get_board("Hooks")
    client.list_monitor_changes()
    client.get_ad("c/1")
    assert {r.method for r in seen} == {"GET"}
    assert all(r.headers["accept"] == "text/markdown" and r.headers["authorization"] == "Bearer tok" for r in seen)
    assert [r.url.raw_path.split(b"?")[0] for r in seen] == [
        b"/api/discovery/stored-results", b"/api/boards/items", b"/api/monitors/events", b"/api/creatives/c%2F1"]
    assert seen[0].url.params["min_days"] == "30"
    assert helix_client.READ_ONLY_METHOD == "GET"
    source = inspect.getsource(helix_client)
    for call in (".post(", ".put(", ".patch(", ".delete(", ".stream("):
        assert call not in source


def test_mcp_client_reports_404_and_auth_without_raising():
    client = helix_client.HelixClient(
        "http://api.test/api", "tok",
        transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"detail": "No finished search"})),
    )
    assert "No finished search" in client.search_ads("x")
    client = helix_client.HelixClient("http://api.test/api", "tok", transport=httpx.MockTransport(lambda r: httpx.Response(403)))
    assert "Not allowed" in client.get_ad("a")
    with pytest.raises(helix_client.HelixError):
        helix_client.HelixClient("http://api.test/api", "")
