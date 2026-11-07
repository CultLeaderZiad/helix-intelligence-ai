"""Hard stops for paid provider calls, independent of credits.

* ``DISCOVER_ENABLED=false`` pauses Discover: no new searches, no monitor
  runs, and queued jobs stop before their first provider call (refunded).
* ``DISCOVER_DAILY_PROVIDER_CALL_CAP`` caps paid provider calls (ad-library
  providers and query translation) across all workspaces per UTC day.
* ``DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE`` caps one workspace's share,
  so a single workspace cannot use up the global budget.
* ``DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY`` caps searches a workspace
  starts per UTC day (cache hits do not count).

Counters live in ``provider_call_budget`` (global) and
``workspace_daily_usage`` (per workspace). Each reservation is an atomic upsert
in its own short transaction; a refused reservation is rolled back so it does
not count. Refunds never touch these counters: a refunded search still counts
toward every cap. Any error reaching a counter refuses the call (fails closed).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

PAUSED = "paused"
BUDGET = "budget"
WORKSPACE_BUDGET = "workspace_budget"

_DAY = "(now() AT TIME ZONE 'utc')::date"
_RESERVE_SQL = text(
    "INSERT INTO provider_call_budget (day, calls, updated_at) "
    f"VALUES ({_DAY}, 1, now()) "
    "ON CONFLICT (day) DO UPDATE SET calls = provider_call_budget.calls + 1, updated_at = now() "
    "RETURNING calls"
)
_WORKSPACE_CALL_SQL = text(
    "INSERT INTO workspace_daily_usage (day, org_id, searches, provider_calls, updated_at) "
    f"VALUES ({_DAY}, :org_id, 0, 1, now()) "
    "ON CONFLICT (day, org_id) DO UPDATE SET "
    "provider_calls = workspace_daily_usage.provider_calls + 1, updated_at = now() "
    "RETURNING provider_calls"
)
_WORKSPACE_SEARCH_SQL = text(
    "INSERT INTO workspace_daily_usage (day, org_id, searches, provider_calls, updated_at) "
    f"VALUES ({_DAY}, :org_id, 1, 0, now()) "
    "ON CONFLICT (day, org_id) DO UPDATE SET "
    "searches = workspace_daily_usage.searches + 1, updated_at = now() "
    "RETURNING searches"
)


def discover_paused() -> bool:
    return not settings.DISCOVER_ENABLED


def _org(org_id: Optional[str]) -> Optional[str]:
    value = str(org_id or "").strip()
    return value if value and value.lower() != "none" else None


async def reserve_provider_call(provider: str, org_id: Optional[str] = None) -> str | None:
    """Reserve one paid call. Returns None when allowed, else PAUSED, BUDGET or WORKSPACE_BUDGET."""
    if discover_paused():
        return PAUSED
    cap = int(settings.DISCOVER_DAILY_PROVIDER_CALL_CAP)
    if cap <= 0:
        return BUDGET
    workspace = _org(org_id)
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            calls = (await db.execute(_RESERVE_SQL)).scalar_one()
            if calls > cap:
                await db.rollback()
                logger.warning("Daily provider call cap reached (%s); refused %s call", cap, provider)
                return BUDGET
            if workspace:
                workspace_cap = int(settings.DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE)
                used = (await db.execute(_WORKSPACE_CALL_SQL, {"org_id": workspace})).scalar_one()
                if workspace_cap <= 0 or used > workspace_cap:
                    await db.rollback()
                    logger.warning("Workspace provider call cap reached for %s; refused %s call", workspace, provider)
                    return WORKSPACE_BUDGET
            await db.commit()
            return None
    except Exception as exc:  # fail closed
        logger.error("Provider budget unavailable; refusing %s call: %s", provider, exc)
        return BUDGET


async def reserve_search_slot(org_id: str) -> bool:
    """Count one new search for the workspace today; False when over the daily cap.

    Committed on its own so it stays counted even if the search later fails
    or is refunded.
    """
    cap = int(settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY)
    workspace = _org(org_id)
    if cap <= 0 or workspace is None:
        return False
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            used = (await db.execute(_WORKSPACE_SEARCH_SQL, {"org_id": workspace})).scalar_one()
            if used > cap:
                await db.rollback()
                return False
            await db.commit()
            return True
    except Exception as exc:  # fail closed
        logger.error("Search counter unavailable; refusing search for %s: %s", workspace, exc)
        return False
