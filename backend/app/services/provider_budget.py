"""Global hard stop for paid provider calls.

Two server-side controls, independent of any one workspace's credits:

* ``DISCOVER_ENABLED=false`` pauses Discover: no new searches, no monitor
  runs, and queued jobs stop before their first provider call (refunded).
* ``DISCOVER_DAILY_PROVIDER_CALL_CAP`` caps paid provider calls (ad-library
  providers and query translation) across all workspaces per UTC day. A call
  is reserved before it is made; past the cap it is refused, not queued.

The counter is one row per UTC day in ``provider_call_budget``, incremented
with an atomic upsert in its own short transaction. A refused reservation is
rolled back so it does not count. Any error reaching the counter refuses the
call: an outage in the guard must not turn into unlimited spend.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

PAUSED = "paused"
BUDGET = "budget"

_RESERVE_SQL = text(
    "INSERT INTO provider_call_budget (day, calls, updated_at) "
    "VALUES ((now() AT TIME ZONE 'utc')::date, 1, now()) "
    "ON CONFLICT (day) DO UPDATE SET calls = provider_call_budget.calls + 1, updated_at = now() "
    "RETURNING calls"
)


def discover_paused() -> bool:
    return not settings.DISCOVER_ENABLED


async def reserve_provider_call(provider: str) -> str | None:
    """Reserve one paid call. Returns None when allowed, else PAUSED or BUDGET."""
    if discover_paused():
        return PAUSED
    cap = int(settings.DISCOVER_DAILY_PROVIDER_CALL_CAP)
    if cap <= 0:
        return BUDGET
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            calls = (await db.execute(_RESERVE_SQL)).scalar_one()
            if calls > cap:
                await db.rollback()
                logger.warning("Daily provider call cap reached (%s); refused %s call", cap, provider)
                return BUDGET
            await db.commit()
            return None
    except Exception as exc:  # fail closed
        logger.error("Provider budget unavailable; refusing %s call: %s", provider, exc)
        return BUDGET
