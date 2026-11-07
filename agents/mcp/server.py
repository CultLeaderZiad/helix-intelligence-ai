"""Helix read-only MCP server: competitor ads your agents can read.

Tools (all read-only, all answer in Markdown):
  search_ads(query, min_days, sort)   stored results of a search your workspace already ran
  get_board(board)                    one of your boards
  list_monitor_changes(monitor_id)    new / stopped / rewritten ads your monitors found
  get_ad(ad_id)                       one ad in full

Run (stdio):  HELIX_API_URL=... HELIX_ACCESS_TOKEN=... python agents/mcp/server.py
"""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from helix_client import HelixClient

mcp = FastMCP("helix")
_client: Optional[HelixClient] = None


def client() -> HelixClient:
    global _client
    if _client is None:
        _client = HelixClient()
    return _client


@mcp.tool()
def search_ads(query: str, min_days: int = 0, sort: str = "days_active_desc") -> str:
    """Meta ads from the latest search your workspace already ran for `query`, longest-running first.

    Never starts a new search or spends credits. min_days may be 30, 60 or 90;
    ads with an unknown run length are then excluded and counted.
    """
    return client().search_ads(query, min_days=min_days, sort=sort)


@mcp.tool()
def get_board(board: str) -> str:
    """The ads saved in one of your boards (by board name)."""
    return client().get_board(board)


@mcp.tool()
def list_monitor_changes(monitor_id: Optional[str] = None, limit: int = 50) -> str:
    """Recent changes your monitors recorded: new ads, ads that stopped, copy changes."""
    return client().list_monitor_changes(monitor_id, limit)


@mcp.tool()
def get_ad(ad_id: str) -> str:
    """One ad in full: text, run length, text-rubric score, Ad Library link."""
    return client().get_ad(ad_id)


if __name__ == "__main__":
    mcp.run()
