"""Hard stops for paid provider calls, independent of credits.

* ``DISCOVER_ENABLED=false`` pauses Discover: no new searches, no monitor
  runs, and queued jobs stop before their first provider call (refunded).
* ``DISCOVER_DAILY_PROVIDER_CALL_CAP`` caps paid provider calls (ad-library
  providers and query translation) across all workspaces per UTC day.
* ``DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE`` caps one workspace's share,
  so a single workspace cannot use up the global budget.
* ``DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY`` caps searches a workspace
  starts per UTC day (cache hits do not count).
* A workspace's plan can override both per-workspace caps (``plans.limits``:
  ``searches_per_day``; its provider-call cap becomes twice that). The global
  daily cap still applies on top.

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
RECORD_BUDGET = "record_budget"

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


_PLAN_LIMITS_SQL = text(
    "SELECT p.limits FROM organizations o JOIN plans p ON p.id = o.plan_id WHERE o.id = :org_id"
)


async def plan_limits(db, org_id: Optional[str]) -> dict:
    """The workspace plan's limits (plans.limits), or {} for global defaults."""
    workspace = _org(org_id)
    if not workspace:
        return {}
    row = (await db.execute(_PLAN_LIMITS_SQL, {"org_id": workspace})).first()
    limits = row[0] if row else None
    return limits if isinstance(limits, dict) else {}


def search_cap(limits: dict) -> int:
    value = limits.get("searches_per_day")
    return int(settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY) if value is None else int(value)


def workspace_call_cap(limits: dict) -> int:
    """A brand search can use two provider tasks, so a plan's cap is 2x its searches."""
    base = int(settings.DISCOVER_DAILY_PROVIDER_CALLS_PER_WORKSPACE)
    value = limits.get("searches_per_day")
    return base if value is None else max(base, 2 * int(value))


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
                workspace_cap = workspace_call_cap(await plan_limits(db, workspace))
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
    workspace = _org(org_id)
    if workspace is None:
        return False
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            cap = search_cap(await plan_limits(db, workspace))
            if cap <= 0:
                return False
            used = (await db.execute(_WORKSPACE_SEARCH_SQL, {"org_id": workspace})).scalar_one()
            if used > cap:
                await db.rollback()
                return False
            await db.commit()
            return True
    except Exception as exc:  # fail closed
        logger.error("Search counter unavailable; refusing search for %s: %s", workspace, exc)
        return False


_RECORDS_SQL = text(
    "INSERT INTO provider_record_budget (provider, period_start, records, updated_at) "
    "VALUES (:provider, date_trunc('month', now() AT TIME ZONE 'utc')::date, :n, now()) "
    "ON CONFLICT (provider, period_start) DO UPDATE SET "
    "records = provider_record_budget.records + :n, updated_at = now() "
    "RETURNING records"
)
_WORKSPACE_RECORDS_SQL = text(
    "INSERT INTO workspace_daily_usage (day, org_id, searches, provider_calls, metapi_records, updated_at) "
    f"VALUES ({_DAY}, :org_id, 0, 0, :n, now()) "
    "ON CONFLICT (day, org_id) DO UPDATE SET "
    "metapi_records = workspace_daily_usage.metapi_records + :n, updated_at = now()"
)
_MONTH = "date_trunc('month', now() AT TIME ZONE 'utc')::date"
_WORKSPACE_MONTH_SQL = text(
    "SELECT coalesce(sum(metapi_records), 0) FROM workspace_daily_usage "
    f"WHERE org_id = :org_id AND day >= {_MONTH}"
)
_MONTH_START_SQL = text(f"SELECT {_MONTH}")

# What one Discover search or monitor run can reserve at most: the keyword
# task (METAPI_RESOLVE_COUNT) plus the advertiser task that loads a matched
# brand page (DISCOVER_MAX_RECORDS). A page-id query uses only the second.
DISCOVER_MAX_RECORDS = 15
RUNS_PER_MONTH = {"daily": 31, "weekly": 5}


def search_record_estimate() -> int:
    return int(settings.METAPI_RESOLVE_COUNT) + DISCOVER_MAX_RECORDS


def monitor_month_estimate(cadence: str) -> int:
    return RUNS_PER_MONTH.get(cadence, 31) * search_record_estimate()


def workspace_record_cap(limits: dict) -> int:
    """Monthly Metapi records for one workspace: the plan's ``records_per_month``
    (set by an admin in the plan editor) or METAPI_WORKSPACE_MONTHLY_RECORD_CAP."""
    value = limits.get("records_per_month")
    return int(settings.METAPI_WORKSPACE_MONTHLY_RECORD_CAP) if value is None else int(value)


async def workspace_record_usage(db, org_id: str) -> dict:
    """This month's Metapi records for one workspace, its cap and the 80% warning."""
    cap = workspace_record_cap(await plan_limits(db, org_id))
    used = int((await db.execute(_WORKSPACE_MONTH_SQL, {"org_id": org_id})).scalar_one() or 0)
    period_start = (await db.execute(_MONTH_START_SQL)).scalar_one()
    percent = 100 if cap <= 0 else min(100, round(100 * used / cap))
    return {
        "period_start": period_start.isoformat(),
        "used": used,
        "cap": cap,
        "remaining": max(0, cap - used),
        "percent": percent,
        "warning": cap <= 0 or used >= 0.8 * cap,
        "reached": used >= cap,
        "estimates": {
            "discover_search": search_record_estimate(),
            "monitor_run": search_record_estimate(),
            "monitor_month": {c: monitor_month_estimate(c) for c in RUNS_PER_MONTH},
        },
    }


def record_cap_error(usage: dict, needed: int) -> dict:
    return {
        "code": "workspace_record_cap_reached",
        "message": (
            f"This workspace has used {usage['used']} of its {usage['cap']} Metapi records this month "
            f"and this needs up to {needed}. Stored results and your archive stay searchable. "
            "Resets on the 1st (UTC); an admin can raise the cap."
        ),
        "used": usage["used"],
        "cap": usage["cap"],
        "needed": needed,
    }


async def assert_record_room(db, org_id: str, needed: int) -> None:
    """Refuse (429) before a search or monitor starts if the cap leaves no room."""
    from fastapi import HTTPException

    usage = await workspace_record_usage(db, org_id)
    if usage["remaining"] < needed:
        raise HTTPException(status_code=429, detail=record_cap_error(usage, needed))


async def reserve_provider_records(
    provider: str, records: int, monthly_budget: int, org_id: Optional[str] = None
) -> bool:
    """Reserve ``records`` against a provider's monthly record budget and,
    with ``org_id``, against that workspace's monthly record cap.

    Metapi bills records, so each task reserves its ``count`` before it is
    created. Both counters move in one transaction: a refusal by either rolls
    back both. Errors refuse (fail closed). Refunds never lower the counters.
    """
    n = max(0, int(records))
    if monthly_budget <= 0 or n == 0:
        return n == 0 and monthly_budget > 0
    workspace = _org(org_id)
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            used = (await db.execute(_RECORDS_SQL, {"provider": provider, "n": n})).scalar_one()
            if used > monthly_budget:
                await db.rollback()
                logger.warning("%s monthly record budget reached (%s); refused %s records", provider, monthly_budget, n)
                return False
            if workspace:
                cap = workspace_record_cap(await plan_limits(db, workspace))
                # Today's row is the only one written, so concurrent
                # reservations serialize on its row lock.
                await db.execute(_WORKSPACE_RECORDS_SQL, {"org_id": workspace, "n": n})
                month = int((await db.execute(_WORKSPACE_MONTH_SQL, {"org_id": workspace})).scalar_one() or 0)
                if cap <= 0 or month > cap:
                    await db.rollback()
                    logger.warning("Workspace record cap reached for %s (%s); refused %s records", workspace, cap, n)
                    return False
            await db.commit()
            return True
    except Exception as exc:  # fail closed
        logger.error("Record budget unavailable; refusing %s task: %s", provider, exc)
        return False
