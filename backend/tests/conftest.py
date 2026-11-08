"""Keep the pooled API engine off closed pytest-asyncio loops.

Background workers such as the scout claim path use ``async_session_maker``.
That pool binds connections to the test's event loop. pytest-asyncio closes
the loop when the test ends, and the next checkout then dies in
``AsyncAdaptedQueuePool`` with ``RuntimeError: Event loop is closed``.
Dispose the pool while this test's loop is still running.
"""

from __future__ import annotations

import pytest_asyncio

from app.db.session import engine


@pytest_asyncio.fixture(autouse=True)
async def _dispose_pooled_engine_after_async_test():
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _provider_budget_allows_calls(request, monkeypatch):
    """Stubbed provider tests must not share or exhaust the real daily counter.

    tests/test_w8_provider_budget.py opts out with the ``real_provider_budget``
    marker and exercises the counter against the database.
    """
    if request.node.get_closest_marker("real_provider_budget"):
        yield
        return
    from app.services import provider_budget

    async def _allow(_provider, org_id=None):
        return None

    async def _allow_records(_provider, _records, _budget):
        return True

    monkeypatch.setattr(provider_budget, "reserve_provider_call", _allow)
    monkeypatch.setattr(provider_budget, "reserve_provider_records", _allow_records)
    yield
