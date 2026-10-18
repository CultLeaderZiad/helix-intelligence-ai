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
